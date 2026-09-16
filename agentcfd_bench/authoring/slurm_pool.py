"""Standalone cluster-side shared-node queue (Python 3.6+).

One allocation, up to ten exact one-CPU srun steps. Never restarts a step after
an ambiguous launch. All files and temporary state stay under the approved root.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import time

PREFIX = '/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/'


def scoped(path):
    value = Path(path)
    if not str(value).startswith(PREFIX) or '..' in value.parts or not str(value.resolve()).startswith(PREFIX):
        raise ValueError('Shared-node queue path outside approved WORK/Caifeixue scope')
    return value


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value, replace=False):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with temp.open('w') as out:
        json.dump(value, out, sort_keys=True, allow_nan=False)
        out.flush()
        os.fsync(out.fileno())
    if replace:
        os.replace(str(temp), str(path))
    else:
        os.link(str(temp), str(path))
        temp.unlink()


def run_command(argv):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


def acquire(root, settings):
    """Called under the queue lock; a lost receipt is discovered, not resubmitted."""
    record = root / 'allocation.json'
    if record.exists():
        return read(record)
    name = 'acfd-pool-' + settings['identity']
    if (root / 'allocation-intent.json').exists():
        found = set()
        for argv in (['squeue', '--me', '-h', '-n', name, '-o', '%i|%j'],
                     ['sacct', '-n', '-X', '--name', name, '-o', 'JobIDRaw,JobName%64', '-P']):
            result = run_command(argv)
            for line in result.stdout.splitlines():
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2 and parts[0].isdigit() and parts[1] == name:
                    found.add(parts[0])
        if len(found) != 1:
            raise RuntimeError('Shared allocation acceptance unknown; refusing duplicate sbatch')
        value = {'job_id': next(iter(found)), 'job_name': name, 'recovered': True}
    else:
        save(root / 'allocation-intent.json', {'job_name': name, 'time': time.time()})
        command = 'exec ' + ' '.join(shlex.quote(x) for x in ['/usr/bin/python3', str(root / 'pool.py'), 'serve', str(root)])
        argv = ['sbatch', '--parsable', '--no-requeue', '--nodes=1', '--ntasks=64', '--cpus-per-task=1',
                '--mem=65536M', '--time=0', '--partition=' + settings['partition'], '--job-name=' + name,
                '--chdir=' + str(root), '--output=' + str(root / 'allocation-%j.out'),
                '--error=' + str(root / 'allocation-%j.err'), '--wrap=' + command]
        result = run_command(argv)
        job = result.stdout.strip().split(';')[0]
        if result.returncode or not job.isdigit():
            save(root / 'allocation-rejected.json', {'code': result.returncode, 'stderr': result.stderr})
            raise RuntimeError('Shared allocation rejected: ' + result.stderr)
        value = {'job_id': job, 'job_name': name, 'recovered': False}
    save(record, value)
    return value


def enqueue(root, operation):
    root, operation = scoped(root), scoped(operation)
    settings = read(root / 'settings.json')
    if not re.fullmatch(r'r-[a-f0-9]{16}', operation.name) or operation.parent != Path(settings['operations']):
        raise ValueError('Operation is not a member of this shared-node campaign')
    with (root / 'queue.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (root / 'stopping.json').exists() or (root / 'finished.json').exists():
            raise RuntimeError('Shared-node queue is closed; do not silently create another allocation')
        if not (operation / 'uploaded.json').exists():
            raise ValueError('Unstaged operation')
        allocation = acquire(root, settings)
        record = operation / 'slurm-job.json'
        if record.exists():
            if read(record)['job_id'] != allocation['job_id']:
                raise ValueError('Operation already belongs to a different allocation')
        else:
            save(record, dict(allocation, shared_pool=str(root)))
        queued = root / 'queue' / (operation.name + '.json')
        if not queued.exists():
            save(queued, {'operation': str(operation), 'queued_at': time.time()})
        save(root / 'heartbeat.json', {'time': time.time()}, replace=True)
        return read(record)


def step_command(job_id, operation):
    return ['srun', '--jobid=' + job_id, '--nodes=1', '--ntasks=1', '--cpus-per-task=1',
            '--exclusive', '--exact', '--mem=4096M', '--cpu-bind=cores',
            '/usr/bin/python3', str(operation / 'job.py'), str(operation)]


def serve(root):
    root = scoped(root)
    settings = read(root / 'settings.json')
    job_id = os.environ['SLURM_JOB_ID']
    with (root / 'server.lock').open('a') as server_lock:
        fcntl.flock(server_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists():
            raise RuntimeError('Shared server already started; no implicit restart of native steps')
        save(root / 'started.json', {'job_id': job_id, 'node': socket.gethostname(), 'time': time.time()})
        active = {}
        peak = 0
        while True:
            for key, (child, operation, out, err) in list(active.items()):
                code = child.poll()
                if code is None:
                    continue
                out.close()
                err.close()
                if not (operation / 'result.json').exists() and not (operation / 'execution-error.json').exists():
                    save(operation / 'execution-error.json', {'type': 'SlurmStepFailure', 'code': code,
                        'message': (operation / 'step.stderr.log').read_text(errors='replace')[-4000:]})
                save(root / 'done' / (key + '.json'), {'step_exit_code': code, 'operation': str(operation), 'time': time.time()})
                del active[key]
            with (root / 'queue.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                queued = [p for p in (root / 'queue').glob('*.json') if not (root / 'done' / p.name).exists() and p.stem not in active]
                queued.sort(key=lambda p: (read(p)['queued_at'], p.name))
                for queued_path in queued[:max(0, settings['max_parallel'] - len(active))]:
                    operation = scoped(read(queued_path)['operation'])
                    if (operation / 'step-dispatch.json').exists():
                        raise RuntimeError('Unresolved previous step dispatch: refuse execution replay')
                    save(operation / 'step-dispatch.json', {'allocation_id': job_id, 'time': time.time()})
                    out = (operation / 'step.stdout.log').open('xb')
                    err = (operation / 'step.stderr.log').open('xb')
                    try:
                        child = subprocess.Popen(step_command(job_id, operation), stdout=out, stderr=err,
                                                 stdin=subprocess.DEVNULL, cwd=str(operation))
                    except OSError as exc:
                        out.close(); err.close()
                        save(operation / 'execution-error.json', {'type': type(exc).__name__, 'message': str(exc)})
                        save(root / 'done' / queued_path.name, {'launch_error': str(exc)})
                    else:
                        active[queued_path.stem] = (child, operation, out, err)
                peak = max(peak, len(active))
                left = [p for p in (root / 'queue').glob('*.json') if not (root / 'done' / p.name).exists()]
                heartbeat = read(root / 'heartbeat.json')['time'] if (root / 'heartbeat.json').exists() else 0
                if not left and not active and ((root / 'stopping.json').exists() or time.time() - heartbeat > settings['orphan_idle_seconds']):
                    save(root / 'finished.json', {'job_id': job_id, 'time': time.time(), 'peak_parallel': peak,
                        'reason': 'controller_finished' if (root / 'stopping.json').exists() else 'orphan_idle_timeout'})
                    break
                save(root / 'state.json', {'job_id': job_id, 'node': socket.gethostname(), 'active': list(active),
                     'queued_or_active': len(left), 'peak_parallel': peak, 'time': time.time()}, replace=True)
            time.sleep(0.2)


def control(root, action):
    root = scoped(root)
    with (root / 'queue.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if action == 'heartbeat':
            save(root / 'heartbeat.json', {'time': time.time()}, replace=True)
        elif action == 'stop':
            if not (root / 'stopping.json').exists():
                save(root / 'stopping.json', {'time': time.time(), 'mode': 'drain_existing_steps'})
        else:
            raise ValueError('Unknown pool control')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['serve', 'enqueue', 'heartbeat', 'stop'])
    parser.add_argument('root')
    parser.add_argument('operation', nargs='?')
    args = parser.parse_args()
    if args.action == 'serve':
        serve(args.root)
    elif args.action == 'enqueue':
        print(json.dumps(enqueue(args.root, args.operation)))
    else:
        control(args.root, args.action)
