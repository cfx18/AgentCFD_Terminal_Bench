"""Detach one qualified, frozen experiment. No retries of unknown launches.

python -m agentcfd_bench.launch experiment.yaml --allow-paid
The returned run directory contains controller.log and all live trial transcripts.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from .tasks.experiment import load, prepare, archive
from .records.store import read, write_once, digest, lock


def alive(process):
    try:
        fields = Path(f'/proc/{process["pid"]}/stat').read_text().rsplit(')', 1)[1].split()
        return (fields[0] != 'Z' and fields[19] == process['start_ticks'] and
                Path('/proc/sys/kernel/random/boot_id').read_text().strip() == process['boot_id'])
    except (OSError, KeyError, IndexError):
        return False


def launch(experiment):
    config, _ = load(experiment)
    parent = Path(config['output']); parent.mkdir(parents=True, exist_ok=True)
    config_identity = digest(config)
    with lock(parent / 'launch.lock'):
        for intent in parent.glob('*/launch-intent.json'):
            if read(intent)['config_identity'] != config_identity:
                continue
            receipt = intent.parent / 'launch.json'
            if not receipt.exists():
                raise RuntimeError('Prior launch outcome unknown; inspect ' + str(intent.parent))
            previous = read(receipt)
            if alive(previous):
                return {'run_id':str(intent.parent), 'pid':previous['pid'], 'already_running':True}
        qualification = prepare(experiment)
        if not qualification['ready']:
            raise RuntimeError('Preparation blocked: ' + '; '.join(qualification['blockers']))
        root = archive(experiment)
        write_once(root / 'preparation.json', qualification)
        argv = [sys.executable, '-B', '-m', 'agentcfd_bench', 'resume', str(root), '--allow-paid']
        write_once(root / 'launch-intent.json', {'config_identity':config_identity, 'argv':argv})
        with (root / 'controller.log').open('xb') as log:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                start_new_session=True, cwd=root / 'code',
                env={**os.environ, 'PYTHONPATH':str(root / 'code'), 'PYTHONDONTWRITEBYTECODE':'1'})
        try:
            ticks = Path(f'/proc/{child.pid}/stat').read_text().rsplit(')',1)[1].split()[19]
        except (OSError, IndexError):
            ticks = None
        process = {'pid':child.pid, 'start_ticks':ticks,
                   'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
        write_once(root / 'launch.json', process)
        return {'run_id':str(root), 'pid':child.pid, 'already_running':False,
                'controller_log':str(root / 'controller.log')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment')
    parser.add_argument('--allow-paid', action='store_true')
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error('Explicit --allow-paid is required')
    import json
    print(json.dumps(launch(args.experiment), ensure_ascii=False, indent=2))
