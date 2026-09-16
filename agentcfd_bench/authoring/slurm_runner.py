"""The same native tool protocol, with independent SSH/Slurm execution workers."""
import re
from pathlib import Path, PurePosixPath

from ..execution.runner import Runner
from ..records.store import read, write_once

WORK = '/public3/home/sca2070/WORK/Caifeixue'


def validate_remote(config):
    root = config['root']
    if (config['host'] != 'sca2070' or not root.startswith(WORK + '/AgentCFD_Terminal_Bench/')
            or '..' in PurePosixPath(root).parts or not re.fullmatch(r'[A-Za-z0-9_./-]+', root)):
        raise ValueError('Remote writes must stay in the dedicated WORK/Caifeixue benchmark directory')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', config['partition']):
        raise ValueError('Invalid partition')
    for name in ('runtime', 'python', 'apptainer', 'image'):
        if not config[name].startswith('/') or '..' in PurePosixPath(config[name]).parts:
            raise ValueError('Trusted absolute runtime paths required')
    if config.get('pool'):
        pool = config['pool']
        path = PurePosixPath(pool['root'])
        if (not str(path).startswith(WORK + '/AgentCFD_Terminal_Bench/') or '..' in path.parts
                or pool['max_parallel'] != 10 or pool['allocation_cpus'] != 64 or pool['step_cpus'] != 1
                or pool['operations'] != root):
            raise ValueError('Shared pool must use the authorized one-node, ten-step policy and same operation root')
    return config


class SlurmRunner(Runner):
    def __init__(self, root, sandbox, *, remote):
        super().__init__(root, sandbox, seconds=None)
        self.remote = validate_remote(remote)
        path = self.root / 'remote-runtime.json'
        if path.exists():
            if read(path) != remote:
                raise ValueError('Cannot resume a native history with a different remote runtime')
        else:
            write_once(path, remote)

    def dispatch_worker(self, root):
        write_once(root / 'remote-config.json', self.remote)
        return super().dispatch_worker(root, 'agentcfd_bench.authoring.slurm_transport')

    def status(self, run_id):
        root = self.directory(run_id)
        if (root / 'result.json').exists():
            return read(root / 'result.json')
        if (root / 'transport-error.json').exists():
            return {'run_id': run_id, 'lifecycle': 'interrupted',
                    'reason': 'remote_transport_error', **read(root / 'transport-error.json')}
        progress = read(root / 'remote-progress.json') if (root / 'remote-progress.json').exists() else {}
        worker = read(root / 'worker.json') if (root / 'worker.json').exists() else {}
        alive = False
        try:
            fields = Path(f"/proc/{worker['pid']}/stat").read_text().rsplit(')', 1)[1].split()
            alive = fields[0] != 'Z' and fields[19] == worker['start_ticks']
        except (OSError, KeyError, IndexError):
            pass
        return {'run_id': run_id, 'lifecycle': 'running' if alive else 'interrupted',
                'reason': 'remote_execution_in_progress' if alive else 'remote_worker_exit_evidence_missing',
                **progress}

    def cancel(self, run_id):
        root = self.directory(run_id)
        if not (root / 'cancel.json').exists():
            write_once(root / 'cancel.json', {'requested': True})
        return self.status(run_id)
