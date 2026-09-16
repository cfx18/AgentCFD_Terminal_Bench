"""Real, bounded Slurm/Apptainer/native integration check. No model requests."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import time

from ..execution.sandbox import Sandbox
from ..records.store import read, write_once
from .slurm_runner import SlurmRunner

PROJECT = Path(__file__).resolve().parents[2]


def wait_for(runner, operation, timeout=600):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        result = runner.status(operation['run_id'])
        if result['lifecycle'] != 'running':
            return result
        time.sleep(1)
    raise TimeoutError('Remote probe did not return terminal evidence; inspect the existing job, do not repeat it')


def probe(config, output, source):
    remote, output, source = read(config), Path(output).resolve(), Path(source)
    output.mkdir(parents=True, exist_ok=False)
    sandbox = Sandbox(foam_root=str(PROJECT / 'environments/native-v2306/foam'), mpi='intelmpi')
    def simple(name, argv, expected):
        root = output / name
        work = root / 'work'
        work.mkdir(parents=True)
        (work / 'marker.txt').write_text('isolated author probe\n')
        runner = SlurmRunner(root / 'native', sandbox, remote=remote)
        operation = runner.start(work, argv, seconds=60)
        result = wait_for(runner, operation)
        if result.get('exit_code') != expected:
            raise RuntimeError(name + ': ' + str(result) + '\n' + runner.logs(operation['run_id'], stream='stderr')['text'])
        runner.verify(operation['run_id'])
        return {'name': name, 'passed': True, 'run_id': operation['run_id'], 'slurm_job_id': result['slurm_job_id'],
                'exit_code': result['exit_code'], 'stdout': runner.logs(operation['run_id'])['text']}
    code = "import os,socket; from pathlib import Path; assert not Path('/public3/home/sca2070').exists(); assert not Path('/root/.ssh').exists(); assert socket.if_nameindex()==[(1,'lo')]; assert Path('/work/marker.txt').exists(); Path('/work/probe.txt').write_text('ok'); print('ISOLATED_REMOTE_NATIVE_OK')"
    with ThreadPoolExecutor(max_workers=2) as pool:
        checks = [pool.submit(simple, 'isolation', ['python3', '-c', code], 0),
                  pool.submit(simple, 'failure', ['sh', '-c', 'echo intentional-native-failure >&2; exit 7'], 7)]
        results = [future.result() for future in checks]
    root = output / 'cavity'
    work = root / 'work'
    shutil.copytree(source, work)
    runner = SlurmRunner(root / 'native', sandbox, remote=remote)
    for argv, kind in [(['blockMesh'], 'exec'), (['icoFoam'], 'run')]:
        operation = runner.start(work, argv, kind=kind, seconds=60)
        result = wait_for(runner, operation)
        if not result.get('success'):
            raise RuntimeError('Original cavity native probe failed: ' + str(result) + '\n' + runner.logs(operation['run_id'], stream='stderr')['text'])
        native, _ = runner.verify(operation['run_id'])
        results.append({'name': argv[0], 'passed': True, 'run_id': operation['run_id'], 'slurm_job_id': result['slurm_job_id']})
        if kind == 'exec':
            shutil.copytree(native / 'artifacts', work, dirs_exist_ok=True)
        else:
            if not (native / 'artifacts/0.5/U').is_file():
                raise ValueError('Original cavity endpoint field missing')
    summary = {'passed': True, 'model_calls': 0, 'checks': results, 'remote': remote,
               'scope': 'Filesystem/network isolation, native nonzero exit, original blockMesh+icoFoam, transfer hashes.'}
    write_once(output / 'qualification.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    print(__import__('json').dumps(probe(args.config, args.output, args.source), ensure_ascii=False, indent=2))
