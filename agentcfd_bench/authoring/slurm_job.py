"""Trusted remote Slurm entry; standalone Python 3.6+ (no project imports).

Only /work is writable in the native container. Host paths and job credentials
are never passed to the model. Exit is fsynced before packaging native outputs.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import time


def save(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with temp.open('x') as stream:
        json.dump(value, stream, allow_nan=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(str(temp), str(path))
    temp.unlink()


def hashes(root):
    result, total = {}, 0
    for folder, dirs, files in os.walk(str(root), followlinks=False):
        for name in dirs:
            if (Path(folder) / name).is_symlink():
                raise ValueError('Directory links are not native evidence')
        for name in files:
            path = Path(folder) / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('Only regular nonlinked artifact files are accepted')
            total += info.st_size
            if total > 2 * 1024**3:
                raise ValueError('Native artifacts exceed 2 GiB transfer safety limit')
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(chunk)
            result[str(path.relative_to(root))] = h.hexdigest()
    return result


def command(root, spec):
    runtime = spec['remote']
    manifest = Path(runtime['runtime']) / 'manifest.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != runtime['runtime_manifest_sha256']:
        raise RuntimeError('Remote OpenFOAM runtime manifest changed')
    argv = [runtime['apptainer'], 'exec', '--containall', '--cleanenv', '--pid',
            '--net', '--network', 'none', '--no-home', '--no-mount', 'hostfs,bind-paths,cwd',
            '--pwd', '/work', '--bind', str(root / 'case') + ':/work',
            '--bind', str(root / 'tmp') + ':/tmp',
            '--bind', runtime['runtime'] + '/content:/opt/foam:ro',
            '--bind', runtime['python'] + ':/opt/python:ro', runtime['image'],
            'env', 'WM_PROJECT_DIR=/opt/foam', 'WM_PROJECT_VERSION=v2306',
            'FOAM_ETC=/opt/foam/etc', 'FOAM_APPBIN=/opt/foam/bin', 'FOAM_LIBBIN=/opt/foam/lib',
            'FOAM_MPI=intelmpi', 'WM_OPTIONS=linux64IccDPInt32Opt',
            'PATH=/opt/foam/bin:/opt/python/bin:/usr/bin:/bin',
            'LD_LIBRARY_PATH=/opt/foam/lib/intelmpi:/opt/foam/lib:/opt/foam/deps:/opt/foam/lib/dummy',
            'OMP_NUM_THREADS=1']
    return argv + spec['argv']


def execute(root):
    root = Path(root).resolve()
    if not str(root).startswith('/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/'):
        raise ValueError('Unexpected remote work root')
    with (root / 'execute.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        spec = json.loads((root / 'spec.json').read_text())
        if (root / 'result.json').exists():
            return
        if not (root / 'exit.json').exists():
            if (root / 'execution-intent.json').exists():
                raise RuntimeError('Previous execution outcome unknown; refusing native replay')
            save(root / 'execution-intent.json', {'pid': os.getpid(), 'slurm_job_id': os.environ.get('SLURM_JOB_ID')})
            for name in ('tmp', 'cache', 'container-config'):
                (root / name).mkdir(exist_ok=True)
            env = dict(os.environ, APPTAINER_CACHEDIR=str(root / 'cache'),
                       APPTAINER_TMPDIR=str(root / 'tmp'), APPTAINER_CONFIGDIR=str(root / 'container-config'),
                       TMPDIR=str(root / 'tmp'))
            started, child = time.monotonic(), None
            receipt = {'exit_code': None, 'termination': 'launch_error', 'elapsed_seconds': 0}
            def limits():
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                limit = spec['sandbox']['file_bytes']
                resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
            with (root / 'stdout.log').open('xb') as out, (root / 'stderr.log').open('xb') as err:
                try:
                    child = subprocess.Popen(command(root, spec), cwd=str(root), stdout=out, stderr=err,
                                             stdin=subprocess.DEVNULL, start_new_session=True, env=env,
                                             preexec_fn=limits)
                    reason = 'exited'
                    while child.poll() is None:
                        if (root / 'cancel.json').exists():
                            reason = 'cancelled'
                        elif spec['seconds'] is not None and time.monotonic() - started >= spec['seconds']:
                            reason = 'budget_exhausted'
                        else:
                            time.sleep(0.1)
                            continue
                        os.killpg(child.pid, signal.SIGKILL)
                        break
                    receipt.update(exit_code=child.wait(), termination=reason)
                except BaseException as exc:
                    if child is not None and child.poll() is None:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                    receipt.update(error_type=type(exc).__name__, message=str(exc))
                receipt['elapsed_seconds'] = time.monotonic() - started
                save(root / 'exit.json', receipt)
                for stream in (out, err):
                    stream.flush()
                    os.fsync(stream.fileno())
        receipt = json.loads((root / 'exit.json').read_text())
        artifacts = hashes(root / 'case')
        for stream in ('stdout', 'stderr'):
            artifacts['@' + stream + '.log'] = hashlib.sha256((root / (stream + '.log')).read_bytes()).hexdigest()
        # Never reexecute the solver on a failed/unfinished collection.
        target = root / 'output.tar.gz'
        if not target.exists():
            temp = root / ('output.tmp-' + str(os.getpid()) + '.tar.gz')
            with tarfile.open(str(temp), 'w:gz') as tar:
                for path in sorted((root / 'case').rglob('*')):
                    if path.is_file():
                        tar.add(str(path), arcname='artifacts/' + str(path.relative_to(root / 'case')), recursive=False)
                for stream in ('stdout.log', 'stderr.log'):
                    tar.add(str(root / stream), arcname=stream, recursive=False)
            temp.rename(target)
        result = dict(receipt, run_id=root.name, kind=spec['kind'], lifecycle='completed', artifacts=artifacts,
                      success=receipt['exit_code'] == 0 and receipt['termination'] == 'exited',
                      transport='ssh-slurm-apptainer-v1', slurm_job_id=os.environ.get('SLURM_JOB_ID'),
                      slurm_step_id=os.environ.get('SLURM_STEP_ID'), node=socket.gethostname(),
                      cpu_affinity=sorted(os.sched_getaffinity(0)))
        save(root / 'result.json', result)


if __name__ == '__main__':
    try:
        execute(sys.argv[1])
    except BaseException as exc:
        save(Path(sys.argv[1]) / 'execution-error.json', {'type': type(exc).__name__, 'message': str(exc)})
        raise
