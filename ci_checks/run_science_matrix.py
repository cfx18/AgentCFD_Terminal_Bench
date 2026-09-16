"""An explicit serial matrix over the existing qualified single-task runner.

No model/solver logic here. Immutable per-task exits and live Chinese summary;
unknown requests are not retried. Resume never relaunches a previously started
trial without an observed exit. Run from a frozen project snapshot.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

from agentcfd_bench.journal import NativeJournal, read_receipt
from agentcfd_bench.reporting import atomic, report
from agentcfd_bench.spec import load_experiment
from agentcfd_bench.task_package import load_task
from agentcfd_bench.qualification import qualify, protocol_identity
from agentcfd_bench.runtime import cluster_service
from agentcfd_bench.science_campaign import process_identity
from agentcfd_bench.signals import interruption_scope
from run_codex_science import ObserveNative, emit
from matrix_lifecycle import RecoveryBlocked, recover_exit, provider_statuses, check_circuit


def summary(root, entries, *, write=True):
    rows = []
    for entry in entries:
        task_id = entry['task']
        trial = root/'trials'/task_id
        exit_receipt = read_receipt(root/'campaign'/(task_id+'.json'))
        row = {'task': task_id, 'status': (exit_receipt or {}).get('status', 'queued')}
        if (trial/'state.sqlite').exists():
            try:
                result = report(trial, write=False)
                row.update({k: result[k] for k in ('lifecycle', 'verdict', 'reason', 'model_calls',
                    'run_submissions', 'native_runs_completed', 'report_failures', 'usage')})
                if exit_receipt:
                    row['status'] = exit_receipt['status']
                elif result['lifecycle'] == 'running':
                    row['status'] = 'running'
                # Inflight requests may not yet be committed to the trial DB.
                requests = list((trial/'agent').glob('*/submission-*/api/call-*/request.json'))
                row['requests_started_live'] = len(requests)
                row['responses_known_live'] = sum(p.with_name('complete.json').exists() for p in requests)
            except Exception as exc:
                row['report_error'] = type(exc).__name__
        rows.append(row)
    value = {'registered': len(rows), 'passed': sum(r.get('verdict') == 'pass' for r in rows),
        'finished': sum(r['status'] not in ('queued', 'running') for r in rows), 'tasks': rows}
    value['paused'] = []
    for path in sorted((root/'campaign').glob('circuit-*.json')):
        if path.stem.endswith('-acknowledged'):
            continue
        if not path.with_name(path.stem+'-acknowledged.json').exists():
            value['paused'].append(read_receipt(path))
    if write:
        atomic(root/'scoreboard.json', json.dumps(value, ensure_ascii=False, indent=2)+'\n')
        names = {'queued': '待开始', 'running': '运行中', 'trial_exited': '已结束',
                 'qualification_failed': '验收环境检查未通过', 'infrastructure_error': '基础设施异常'}
        lines = ['# Science 评测：实时结果', '',
            f"共 {len(rows)} 题；已通过 {value['passed']} 题。未完成和基础设施异常不是模型答错。", '',
            '|题目|状态|验收|已发请求／已返回|OpenFOAM 提交|运行完成|报告未通过|',
            '|---|---|---|---:|---:|---:|---:|']
        for row in rows:
            lines.append('|'+ '|'.join(str(x) for x in (row['task'], names.get(row['status'], row['status']),
                row.get('verdict', '未评分'),
                f"{row.get('requests_started_live', 0)}/{row.get('responses_known_live', 0)}",
                row.get('run_submissions', 0), row.get('native_runs_completed', 0), row.get('report_failures', 0)))+'|')
        lines += ['', '各题完整轨迹见 trials/<题号>/agent/<工作目录>/submission-*/events.jsonl；',
            '原生请求及响应见同目录 api/call-*；不含认证头。',
            '模型、harness 和文档条件见 campaign/spec.json；不同实验不合并计分。', '']
        if value['paused']:
            lines += ['**暂停派发**：'+', '.join(p['reason'] for p in value['paused']),
                      '剩余题目仍计入注册数量；修复后须显式确认恢复，不自动重发此前请求。', '']
        atomic(root/'scoreboard.md', '\n'.join(lines))
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'source-project', 'manifest', 'root', 'probe'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--auth-home')
    parser.add_argument('--env-file')
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--acknowledge-circuit', action='store_true',
                        help='Explicitly acknowledge saved circuits on resume, without retrying old trials')
    args = parser.parse_args(argv)
    if not args.allow_paid:
        parser.error('Explicit --allow-paid required')
    if args.acknowledge_circuit and not args.resume:
        parser.error('--acknowledge-circuit requires --resume')
    project, source, root = map(lambda x: Path(x).resolve(), (args.project, args.source_project, args.root))
    manifest = json.loads(Path(args.manifest).read_text())
    harness_name = manifest.get('harness', 'codex')
    if harness_name not in ('codex', 'foamclaw', 'claude-code', 'kimi-code'):
        parser.error('Unknown harness; no fallback is allowed')
    if (manifest.get('version') != 'explicit-science-matrix-v1' or
            manifest.get('provider_concurrency') != 1 or manifest.get('native_concurrency') != 1):
        parser.error('Explicit serial matrix required')
    probe = read_receipt(Path(args.probe)/'result.json')
    probe_spec = read_receipt(Path(args.probe)/'spec.json')
    from interface_evidence import validate as validate_interface
    validate_interface(manifest.get('interface_check','live-probe'), probe_spec, probe)
    if probe_spec['harness_identity'].get('name', 'codex') != harness_name:
        parser.error('Probe harness differs from matrix')
    entries = []
    for row in manifest['tasks']:
        experiment_path = project/'experiments'/row['experiment']
        experiment = load_experiment(experiment_path)
        task = load_task(experiment['task']['id'], version=experiment['task']['version'])
        if probe_spec['model'] != experiment['model']:
            parser.error('Probe model differs from matrix')
        if (probe_spec['harness_identity'].get('backend', 'custom-api') != experiment.get('harness', {}).get('backend', 'custom-api')
                or probe_spec['harness_identity'].get('reasoning_effort') != experiment.get('harness', {}).get('reasoning_effort')):
            parser.error('Probe backend/reasoning differs from matrix')
        for name, digest in probe_spec['harness_identity'].get('bridge_source_hashes', {}).items():
            import hashlib
            if hashlib.sha256((project/'agentcfd_bench'/name).read_bytes()).hexdigest() != digest:
                parser.error('Bridge changed after real client probe; requalify the interface')
        if experiment.get('harness') and not probe_spec['harness_identity'].get('bridge_source_hashes'):
            parser.error('Native subscription probe lacks source binding')
        entries.append({'task': task.identity['id'], 'experiment': experiment,
            'path': str(experiment_path), 'positive_source': str(source/row['positive_source']) if row['positive_source'] else None,
            'task_binding': task.binding, 'protocol_hash': protocol_identity(task=task)})
    if len({e['task'] for e in entries}) != len(entries):
        parser.error('Duplicate task in matrix')
    root.mkdir(parents=True, exist_ok=args.resume)
    journal = NativeJournal(root/'campaign')
    spec = {'entries': entries, 'probe_root': str(Path(args.probe).resolve()),
            'source_project': str(source), 'manifest': manifest}
    if journal.read('spec') is None:
        journal.write('spec', spec)
    elif journal.read('spec') != spec:
        raise ValueError('Cannot change a started matrix')
    stop = threading.Event()
    def watch():
        while not stop.wait(15):
            try:
                summary(root, entries)
            except Exception as exc:
                emit('matrix_monitor_error', type=type(exc).__name__)
    with interruption_scope(), (root/'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        monitor = threading.Thread(target=watch, daemon=True)
        monitor.start()
        emit('matrix_started', pid=os.getpid(), tasks=[e['task'] for e in entries], root=str(root))
        summary(root, entries)
        try:
            paused = check_circuit(journal, entries, acknowledge=args.acknowledge_circuit)
            if paused:
                emit('matrix_paused', **paused)
                summary(root, entries)
                return 2
            for entry in entries:
                task_id = entry['task']
                if journal.read(task_id) is not None:
                    continue
                task = load_task(task_id, version=entry['experiment']['task']['version'])
                qualification = root/'qualification'/task_id
                try:
                    launch_name = task_id+'-launch'
                    exit_name = task_id+'-exit'
                    previous = journal.read(launch_name)
                    if previous is not None:
                        saved_exit = recover_exit(journal, entry, root/'trials'/task_id,
                                                  identity=process_identity, wait=time.sleep)
                        returncode = saved_exit['returncode']
                    else:
                        emit('qualification_started', task=task_id)
                        service = (None if task.config['metadata'].get('qualification') ==
                                   {'source_mode':'expert-accepted-reference-v1'} else
                                   ObserveNative(cluster_service(qualification/'native', task=task)))
                        result = qualify(qualification, service,
                            task=task, positive_source=entry['positive_source'])
                        emit('qualification_finished', task=task_id, passed=result['passed'], checks=result['checks'])
                        if not result['passed']:
                            journal.write(task_id, {'status': 'qualification_failed', 'checks': result['checks']})
                            continue
                        launch_id = uuid.uuid4().hex
                        command = [sys.executable, '-u', '-B', str(Path(__file__).with_name('run_codex_science.py')),
                            '--harness', harness_name,
                            '--experiment', entry['path'], '--root', str(root/'trials'/task_id),
                            '--qualification', str(qualification), '--legacy-root', str(source.parent),
                            '--launch-id', launch_id, '--allow-paid']
                        if args.auth_home:
                            command += ['--auth-home', args.auth_home]
                        if args.env_file:
                            command += ['--env-file', args.env_file]
                        journal.write(launch_name, {'command': command, 'time': time.time(), 'launch_id': launch_id})
                        emit('trial_started', task=task_id)
                        child = subprocess.Popen(command, start_new_session=True)
                        journal.write(task_id+'-process', {'pid': child.pid, 'identity': process_identity(child.pid)})
                        try:
                            returncode = child.wait()
                        except BaseException:
                            if child.poll() is None:
                                os.killpg(child.pid, signal.SIGTERM)
                            try:
                                child.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid, signal.SIGKILL)
                                child.wait()
                            journal.write(exit_name, {'returncode': child.returncode, 'interrupted': True, 'time': time.time()})
                            raise
                        # Persist observed exit before collecting any report.
                        journal.write(exit_name, {'returncode': returncode, 'time': time.time()})
                    row = {'status': 'trial_exited', 'returncode': returncode,
                           'provider_http_statuses': provider_statuses(root/'trials'/task_id)}
                    if (root/'trials'/task_id/'state.sqlite').exists():
                        data = report(root/'trials'/task_id, write=False)
                        row.update({k:data[k] for k in ('lifecycle', 'verdict', 'reason')})
                    journal.write(task_id, row)
                    emit('trial_exited', task=task_id, returncode=returncode)
                except RecoveryBlocked as exc:
                    emit('matrix_blocked', task=task_id, reason=str(exc))
                    return 2
                except Exception as exc:
                    journal.write(task_id, {'status': 'infrastructure_error', 'type': type(exc).__name__})
                    emit('task_error', task=task_id, type=type(exc).__name__)
                summary(root, entries)
                paused = check_circuit(journal, entries)
                if paused:
                    emit('matrix_paused', **paused)
                    summary(root, entries)
                    return 2
            if journal.read('finished') is None:
                journal.write('finished', summary(root, entries))
            emit('matrix_finished', **summary(root, entries))
        finally:
            stop.set(); monitor.join(timeout=5)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
