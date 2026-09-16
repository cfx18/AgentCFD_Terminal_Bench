"""Detached author-worker supervisor and read-only progress. Never starts evals."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from ..records.store import read, write_once, lock


def retryable_infra_failure(worker_root):
    record = Path(worker_root) / 'result.json'
    if not record.exists():
        return None
    item = read(record)
    harness = item.get('harness', {})
    errors = harness.get('errors') or []
    if not any(error.get('upstream_result_known') is False for error in errors):
        return None
    outputs = item.get('outputs_present') or {}
    if outputs and all(outputs.values()):
        return None
    return {'reason': 'provider_result_unknown', 'retryable': True,
            'model_calls': harness.get('calls'), 'outputs_present': outputs,
            'error_types': sorted({error.get('type', 'unknown') for error in errors})}


def interface_issue(worker_root):
    record = Path(worker_root) / 'result.json'
    if not record.exists():
        return None
    item = read(record)
    harness = item.get('harness', {})
    errors = harness.get('errors') or []
    if not errors:
        return None
    outputs = item.get('outputs_present') or {}
    retryable = retryable_infra_failure(worker_root)
    if retryable:
        return retryable
    if not outputs or not all(outputs.values()):
        return {'reason': 'provider_or_delivery_error_before_materials',
                'retryable': True, 'model_calls': harness.get('calls'),
                'outputs_present': outputs,
                'error_types': sorted({error.get('type', 'unknown') for error in errors})}
    return {'reason': 'provider_or_delivery_error_after_materials',
            'retryable': False, 'model_calls': harness.get('calls'),
            'outputs_present': outputs,
            'error_types': sorted({error.get('type', 'unknown') for error in errors})}


def status(config):
    config = read(config)
    result = {}
    for job in config['jobs']:
        root = Path(config['root']) / 'workers' / job
        if (root / 'result.json').exists():
            item = read(root / 'result.json')
            issue = interface_issue(root)
            lifecycle = ('infra_error' if issue and issue.get('retryable') else
                         'completed_with_interface_error' if issue else 'completed')
            result[job] = {'lifecycle': lifecycle,
                           'model_calls': item['harness']['calls'],
                           'outputs_present': item['outputs_present'], 'release_qualified': False}
            if issue:
                result[job]['infrastructure_error'] = issue
        elif (root / 'interrupted.json').exists():
            result[job] = {'lifecycle': 'interrupted', **read(root / 'interrupted.json')}
        elif (root / 'dispatch.json').exists():
            pid = read(root / 'dispatch.json')['pid']
            result[job] = {'lifecycle': 'running' if Path(f'/proc/{pid}').exists() else 'interrupted',
                           'model_calls_started': len(list(root.glob('agent/calls/turn-*/api/call-*'))),
                           'native_operations': len(list((root / 'native').glob('r-*')))}
        else:
            outcome = root.parent.parent / 'outcomes' / (job + '.json')
            result[job] = {'lifecycle': 'queued', **(read(outcome) if outcome.exists() else {})}
    return {'purpose': 'reference_authoring', 'model': config['model'],
            'target': config['target_qualified_tasks'], 'workers': result}


def batches(config):
    jobs = config.get('job_order', list(config['jobs']))
    if set(jobs) != set(config['jobs']) or len(jobs) != len(config['jobs']):
        raise ValueError('Job order must cover the complete frozen queue exactly once')
    width = config['author_concurrency']
    if type(width) is not int or width < 1:
        raise ValueError('Positive author concurrency required')
    return [jobs[i:i + width] for i in range(0, len(jobs), width)]


def progress(config_path, event, **details):
    config = read(config_path)
    root = Path(config['root'])
    value = {'time': datetime.now(timezone.utc).isoformat(), 'event': event,
             **details, 'status': status(config_path)}
    print(json.dumps(value, ensure_ascii=False), flush=True)
    # This derived convenience view may change. Original receipts are immutable.
    temporary = root / 'progress.latest.json.tmp'
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(root / 'progress.latest.json')
    from .report import markdown
    try:
        temporary = root / 'PROGRESS.zh.md.tmp'
        temporary.write_text(markdown(config_path))
        temporary.replace(root / 'PROGRESS.zh.md')
    except (ValueError, TypeError, OSError) as exc:
        print(json.dumps({'event': 'report_error', 'type': type(exc).__name__, 'message': str(exc)}), flush=True)
    pool_signal(config, 'heartbeat')


def pool_signal(config, action):
    if config.get('remote', {}).get('pool'):
        try:
            from .shared_node import control
            control(config['remote'], action)
        except Exception as exc:
            print(json.dumps({'event': 'pool_control_error', 'action': action,
                              'type': type(exc).__name__, 'message': str(exc)}), flush=True)


def terminal_author(config, job):
    root = Path(config['root'])
    worker = root / 'workers' / job
    return (any((worker / name).exists() for name in ('result.json', 'interrupted.json'))
            or (root / 'outcomes' / (job + '.json')).exists())


def overloaded_jobs(config, jobs):
    """Use actual provider evidence, not an inference from a generic exception."""
    found = []
    for job in jobs:
        worker = Path(config['root']) / 'workers' / job
        record = worker / 'result.json'
        if not record.exists() or not read(record).get('harness', {}).get('errors'):
            continue
        responses = sorted(worker.glob('agent/calls/turn-*/api/call-*/response.raw'))
        if not responses:
            continue
        with responses[-1].open(errors='replace') as stream:
            for line in stream:
                if not line.startswith('data: {'):
                    continue
                try:
                    event = json.loads(line[6:])
                except ValueError:
                    continue
                if (event.get('type') == 'response.failed'
                        and event.get('response', {}).get('error', {}).get('code') == 'server_is_overloaded'):
                    found.append(job)
                    break
    return found


def cooldown(config_path, previous_index, previous_jobs):
    config = read(config_path)
    failed = overloaded_jobs(config, previous_jobs)
    if not failed:
        return
    receipt = Path(config['root']) / 'cooldowns' / f'batch-{previous_index:03d}.json'
    if not receipt.exists():
        write_once(receipt, {'policy': 'author-provider-overload-v1', 'reason': 'server_is_overloaded',
                            'jobs': failed, 'seconds': 600, 'until': time.time() + 600,
                            'replays_previous_requests': False})
    value = read(receipt)
    if time.time() >= value['until']:
        return
    progress(config_path, 'provider_overload_cooldown', **value)
    heartbeat = time.monotonic()
    while time.time() < value['until']:
        time.sleep(max(0, min(30, value['until'] - time.time())))
        if time.monotonic() - heartbeat >= 300:
            progress(config_path, 'provider_overload_cooldown', **value)
            heartbeat = time.monotonic()


def supervise(config_path):
    from .worker import execute
    config = read(config_path)
    root = Path(config['root'])
    with lock(root / 'supervisor.lock'):
        if (root / 'superseded.json').exists():
            raise RuntimeError('Campaign superseded; do not resume its model requests')
        if config.get('after_receipt'):
            receipt = Path(config['after_receipt'])
            progress(config_path, 'waiting_for_migration_drain', receipt=str(receipt))
            heartbeat = time.monotonic()
            while not receipt.exists():
                time.sleep(30)
                if time.monotonic() - heartbeat >= 300:
                    progress(config_path, 'waiting_for_migration_drain', receipt=str(receipt))
                    heartbeat = time.monotonic()
        if config.get('after_campaign'):
            dependency = Path(config['after_campaign'])
            progress(config_path, 'waiting_for_current_pilot', dependency=str(dependency))
            while not (Path(read(dependency)['root']) / 'supervisor-completed.json').exists():
                states = status(dependency)['workers'].values()
                if all(x['lifecycle'] in ('completed', 'interrupted') for x in states):
                    break
                time.sleep(30)
            progress(config_path, 'current_pilot_finished')
        def run(job):
            if terminal_author(config, job):
                return {'job': job, 'existing_receipts_preserved': True, 'model_replayed': False}
            try:
                return execute(config_path, job)
            except Exception as exc:
                result = {'job': job, 'lifecycle': 'interrupted', 'type': type(exc).__name__, 'message': str(exc)}
                write_once(root / 'outcomes' / (job + '.json'), result)
                return result
        previous = None
        for index, batch in enumerate(batches(config), 1):
            if all(terminal_author(config, job) for job in batch):
                previous = (index, batch)
                continue
            if previous:
                cooldown(config_path, *previous)
            progress(config_path, 'batch_started', batch=index, jobs=batch)
            heartbeat = time.monotonic()
            with ThreadPoolExecutor(max_workers=config['author_concurrency']) as pool:
                pending = {pool.submit(run, job) for job in batch}
                while pending:
                    done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)
                    for future in done:
                        print(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                                          'event': 'author_job_finished', 'result': future.result()}), flush=True)
                    if done or time.monotonic() - heartbeat >= 300:
                        progress(config_path, 'progress', batch=index)
                        heartbeat = time.monotonic()
            progress(config_path, 'batch_finished', batch=index)
            previous = (index, batch)
        write_once(root / 'supervisor-completed.json', status(config_path))
        pool_signal(config, 'stop')


def launch(config_path, *, retry_unstarted=False, resume_known=False):
    config_path = Path(config_path).resolve()
    config = read(config_path)
    root = Path(config['root'])
    with lock(root / 'launch.lock'):
        if (root / 'superseded.json').exists():
            raise RuntimeError('Campaign superseded; follow its replacement instead')
        record, log_name = 'launch.json', 'controller.log'
        if resume_known:
            if (root / 'supervisor-completed.json').exists():
                raise RuntimeError('Campaign already finished; do not replay completed work')
            from .migration_gate import process_identity
            prior = read(root / 'launch.json')
            for receipt in sorted(root.glob('launch.resume-*.json')):
                prior = read(receipt)
            identity = process_identity(prior['pid'])
            if identity and identity['state'] != 'Z':
                raise RuntimeError('Previous controller may still be alive')
            for job in config['jobs']:
                if (root / 'workers' / job / 'dispatch.json').exists() and not terminal_author(config, job):
                    raise RuntimeError('Unresolved author request; refusing replay: ' + job)
            number = len(list(root.glob('launch.resume-*.json'))) + 1
            record, log_name = f'launch.resume-{number:03d}.json', f'controller.resume-{number:03d}.log'
        if retry_unstarted:
            previous = read(root / 'launch.json')
            process = Path(f"/proc/{previous['pid']}/stat")
            if process.exists() and process.read_text().rsplit(')', 1)[1].split()[0] != 'Z':
                raise RuntimeError('Previous controller may still be alive')
            if list(root.glob('workers/*/dispatch.json')):
                raise RuntimeError('A job was already dispatched; retry requires evidence review')
            record, log_name = 'launch.retry-001.json', 'controller.retry-001.log'
        if (root / record).exists():
            raise RuntimeError('Campaign already launched; inspect status, no implicit duplicate dispatch')
        with (root / log_name).open('xb') as log:
            child = subprocess.Popen([sys.executable, '-m', 'agentcfd_bench.authoring.control', 'supervise', str(config_path)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
                cwd=Path(__file__).resolve().parents[2])
        value = {'pid': child.pid, 'config': str(config_path),
                 'started': datetime.now(timezone.utc).isoformat(),
                 'account_home': config['harness']['auth_home'], 'model': config['model'],
                 'supervisor_policy': 'author-provider-overload-v1',
                 'preserve_known_terminal_requests': resume_known}
        write_once(root / record, value)
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['launch', 'retry-unstarted', 'resume-known', 'supervise', 'status'])
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    value = ({'launch': launch, 'supervise': supervise, 'status': status}[args.command](args.config)
             if args.command not in ('retry-unstarted', 'resume-known') else
             launch(args.config, **{'retry_unstarted' if args.command == 'retry-unstarted' else 'resume_known': True}))
    if value is not None:
        print(json.dumps(value, ensure_ascii=False, indent=2))
