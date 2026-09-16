"""Hold unstarted worker locks; let active work drain before retiring a controller.

No fabricated dispatch/result records, no model retry and no remote cancellation.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import time

from ..records.store import read, write_once


def process_identity(pid):
    root = Path('/proc') / str(pid)
    try:
        fields = (root / 'stat').read_text().rsplit(')', 1)[1].split()
        return {'state': fields[0], 'ticks': fields[19],
                'command': (root / 'cmdline').read_bytes().replace(b'\0', b' ').decode()}
    except FileNotFoundError:
        return None


def latest_controller(root):
    """The original launch can be dead while a resumed controller is active."""
    receipts = list(Path(root).glob('launch*.json'))
    if not receipts:
        raise ValueError('No controller launch receipt')
    records = [(read(path).get('started', ''), path.name, read(path)) for path in receipts]
    return max(records, key=lambda item: item[:2])[2]


def retire_finished_authors(config_path, output):
    """Retire only the scheduler once all started model interactions ended.

Native workers are independent sessions. Preserve them, including unfinished
operations, instead of making unrelated undispatched authors wait for them.
"""
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    config, gate = read(config_path), read(output / 'gate-ready.json')
    if Path(gate['source_config']).resolve() != config_path:
        raise ValueError('Wrong campaign gate')
    root = Path(config['root'])
    native_pending = []
    for job in gate['existing_jobs']:
        worker = root / 'workers' / job
        if not any((worker / name).exists() for name in ('result.json', 'interrupted.json')):
            if not (root / 'outcomes' / (job + '.json')).exists():
                raise RuntimeError('Author interaction still active: ' + job)
        for run in (worker / 'native').glob('r-*'):
            if (run / 'dispatch.json').exists() and not (run / 'exit.json').exists():
                native_pending.append({'job': job, 'path': str(run),
                    'worker': read(run / 'worker.json') if (run / 'worker.json').exists() else None,
                    'status': 'not_evaluated_pending_exit_evidence'})
    for job in gate['unstarted_jobs']:
        if (root / 'workers' / job / 'dispatch.json').exists():
            raise RuntimeError('A migration target has already started: ' + job)
    pid = gate['controller_pid']
    current = process_identity(pid)
    if (not current or current['state'] == 'Z'):
        return {'controller_already_stopped': True}
    if (current['ticks'] != gate['controller_identity']['ticks']
            or str(config_path) not in current['command']
            or 'agentcfd_bench.authoring.control supervise' not in current['command']):
        raise RuntimeError('Controller identity changed; refusing termination')
    value = {'controller_pid': pid, 'native_workers_preserved': native_pending,
             'all_started_author_interactions_ended': True, 'native_jobs_cancelled': False,
             'note': 'Scheduler retirement only, not a claim that native work completed.'}
    write_once(output / 'controller-retirement-intent.json', value)
    # Do not killpg: native workers must survive the controller handoff.
    os.kill(pid, signal.SIGTERM)
    return value


def hold(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    config = read(config_path)
    root = Path(config['root'])
    output.mkdir(parents=True, exist_ok=True)
    pid = latest_controller(root)['pid']
    identity = process_identity(pid)
    if identity and str(config_path) not in identity['command']:
        raise RuntimeError('Controller process identity does not match the configured campaign')
    handles, pending, active = [], [], []
    for job in config.get('job_order', list(config['jobs'])):
        worker = root / 'workers' / job
        worker.mkdir(parents=True, exist_ok=True)
        handle = (worker / 'worker.lock').open('a')
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            active.append(job)
            continue
        handles.append(handle)
        if (worker / 'dispatch.json').exists() or (worker / 'result.json').exists():
            active.append(job)
        else:
            pending.append(job)
    write_once(output / 'gate-ready.json', {'pid': os.getpid(), 'controller_pid': pid,
        'controller_identity': identity, 'source_config': str(config_path),
        'unstarted_jobs': pending, 'existing_jobs': active,
        'purpose': 'Runtime migration; no API calls or native operations are repeated.'})
    while True:
        unfinished = []
        for job in active:
            worker = root / 'workers' / job
            if not any((worker / name).exists() for name in ('result.json', 'interrupted.json')):
                if not (root / 'outcomes' / (job + '.json')).exists():
                    unfinished.append(job)
                    continue
            if any((run / 'dispatch.json').exists() and not (run / 'exit.json').exists()
                   for run in (worker / 'native').glob('r-*')):
                unfinished.append(job)
        now = process_identity(pid)
        if not now or now['state'] == 'Z':
            break
        if now['ticks'] != identity['ticks'] or str(config_path) not in now['command']:
            raise RuntimeError('Controller PID reused; refusing termination')
        if not unfinished:
            os.kill(pid, signal.SIGTERM)
            while (now := process_identity(pid)) and now['state'] != 'Z' and now['ticks'] == identity['ticks']:
                time.sleep(1)
            break
        time.sleep(10)
    write_once(output / 'drained.json', {'retired_controller_pid': pid,
        'preserved_existing_jobs': active, 'unstarted_jobs': pending,
        'no_model_requests_cancelled': True})
    for handle in handles:
        handle.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--retire-finished-authors', action='store_true')
    args = parser.parse_args()
    if args.retire_finished_authors:
        print(json.dumps(retire_finished_authors(args.config, args.output), ensure_ascii=False))
    else:
        hold(args.config, args.output)
