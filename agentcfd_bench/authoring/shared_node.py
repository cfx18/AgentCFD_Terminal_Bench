"""Local setup/control helpers for a single shared Slurm allocation."""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import uuid

from ..records.store import read, write_once
from .slurm_transport import ssh

PREPARE = r'''
import json,os,pathlib,sys
root=pathlib.Path(sys.argv[1]); settings=json.loads(sys.argv[2])
prefix='/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/'
if not str(root).startswith(prefix) or not os.path.realpath(str(root)).startswith(prefix): raise ValueError('scope')
root.mkdir(parents=True,exist_ok=False)
for name in ('queue','done'): (root/name).mkdir()
with (root/'pool.py').open('xb') as f: f.write(sys.stdin.buffer.read()); f.flush(); os.fsync(f.fileno())
with (root/'settings.json').open('x') as f: json.dump(settings,f); f.flush(); os.fsync(f.fileno())
print('prepared_without_allocation')
'''


def prepare(remote_config, output):
    remote = read(remote_config)
    identity = uuid.uuid4().hex[:16]
    root = str(Path(remote['root']).parent / ('shared-' + identity))
    settings = {'identity': identity, 'operations': remote['root'], 'partition': remote['partition'],
                'max_parallel': 10, 'allocation_cpus': 64, 'step_cpus': 1, 'orphan_idle_seconds': 1800}
    with Path(__file__).with_name('slurm_pool.py').open('rb') as source:
        ssh(remote, ['python3', '-c', PREPARE, root, json.dumps(settings)], input_file=source)
    value = {**remote, 'pool': {'root': root, **settings},
             'scheduling': 'single_64_cpu_node_up_to_10_one_cpu_steps'}
    write_once(output, value)
    return value


def control(remote, action):
    pool = remote['pool']['root']
    return ssh(remote, ['python3', pool + '/pool.py', action, pool])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'heartbeat', 'stop'])
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = prepare(args.config, args.output) if args.action == 'prepare' else control(read(args.config), args.action)
    print(json.dumps(value, ensure_ascii=False, default=str))
