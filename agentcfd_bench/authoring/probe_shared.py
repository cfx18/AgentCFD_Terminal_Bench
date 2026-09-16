"""Prove ten simultaneous isolated steps use one real Slurm node/allocation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .slurm_runner import SlurmRunner
from .probe_slurm import wait_for, probe as native_probe, PROJECT
from .shared_node import control
from ..execution.sandbox import Sandbox
from ..records.store import read, write_once


def probe(config_path, output, source):
    remote, output = read(config_path), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    sandbox = Sandbox(foam_root=str(PROJECT / 'environments/native-v2306/foam'), mpi='intelmpi')
    def one(index):
        root = output / ('step-%02d' % index)
        work = root / 'work'
        work.mkdir(parents=True)
        (work / 'marker').write_text(str(index))
        runner = SlurmRunner(root / 'native', sandbox, remote=remote)
        code = "import os,socket,time; from pathlib import Path; assert not Path('/public3/home/sca2070').exists(); assert socket.if_nameindex()==[(1,'lo')]; print('SHARED_ISOLATED_OK',flush=True); time.sleep(20); raise SystemExit(%d)" % (7 if index == 0 else 0)
        op = runner.start(work, ['python3', '-c', code], seconds=60)
        result = wait_for(runner, op)
        if result.get('exit_code') != (7 if index == 0 else 0):
            raise RuntimeError('Shared-node probe failed: ' + str(result) + '\n' + runner.logs(op['run_id'], stream='stderr')['text'])
        runner.verify(op['run_id'])
        return {key: result[key] for key in ('run_id', 'slurm_job_id', 'slurm_step_id', 'node', 'cpu_affinity', 'exit_code')}
    try:
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(one, range(10)))
        if len({r['slurm_job_id'] for r in results}) != 1 or len({r['node'] for r in results}) != 1:
            raise ValueError('Steps did not share a single allocation/node')
        if len({r['slurm_step_id'] for r in results}) != 10:
            raise ValueError('Distinct Slurm step evidence missing')
        affinities = [set(r['cpu_affinity']) for r in results]
        if any(a & b for i, a in enumerate(affinities) for b in affinities[i + 1:]):
            raise ValueError('Concurrent exact steps unexpectedly overlap CPU affinity')
        # Mesh + solver + failure checks reuse this same shared allocation.
        native = native_probe(config_path, output / 'native-probe', source)
        from .slurm_transport import ssh
        import json
        state = json.loads(ssh(remote, ['cat', remote['pool']['root'] + '/state.json']))
        if state['peak_parallel'] != 10:
            raise ValueError('Ten-way simultaneous scheduling not observed')
        value = {'passed': True, 'model_calls': 0, 'steps': results, 'peak_parallel': state['peak_parallel'],
                 'allocation_id': results[0]['slurm_job_id'], 'node': results[0]['node'], 'native': native,
                 'remote': remote, 'scope': 'one node/one allocation, 10 nonoverlapping steps, isolation, native success/failure, verified transfer'}
        write_once(output / 'qualification.json', value)
        return value
    finally:
        # Only this test pool, graceful drain; never cancels unrelated jobs.
        control(remote, 'stop')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    print(__import__('json').dumps(probe(args.config, args.output, args.source), ensure_ascii=False, indent=2))
