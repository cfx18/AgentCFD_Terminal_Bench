"""Run one explicitly authorized author job through the isolated Codex harness.

An author has access to tutorial sources; an evaluated agent must never use this
entry point. An incomplete/ambiguous provider request is recorded, not retried.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil

from ..execution.runner import Runner
from ..execution.sandbox import Sandbox
from ..harnesses.codex import Codex
from ..records.store import read, write_once, lock


class AuthorRunner(Runner):
    """Do not begin another copy-heavy operation after consuming disk reserve."""
    def __init__(self, root, sandbox, *, reserve):
        super().__init__(root, sandbox, seconds=None)
        self.reserve = reserve

    def start(self, work, argv, *, kind='exec', seconds=None):
        if shutil.disk_usage(self.root).free < self.reserve:
            raise RuntimeError('Author native operation not dispatched: disk reserve reached; preserve current evidence')
        return super().start(work, argv, kind=kind, seconds=seconds)


def validate_model(config):
    if config['model'] == 'gpt-5.6-luna':
        return  # Preserve the original authorized campaigns.
    authorization = config.get('author_model_authorization', {})
    if (config['model'] != 'gpt-5.6-sol' or authorization.get('model') != config['model']
            or authorization.get('user_confirmed') is not True
            or authorization.get('reasoning_effort') != 'high'
            or config['harness'].get('reasoning_effort') != 'high'
            or authorization.get('auth_home') != '/root/.codex-experiment'
            or config['harness']['auth_home'] != '/root/.codex-experiment'):
        raise ValueError('Author model/account is not explicitly authorized for this campaign')


def execute(config_path, job_id):
    config_path = Path(config_path).resolve()
    config = read(config_path)
    job = config['jobs'][job_id]
    root = Path(config['root']) / 'workers' / job_id
    root.mkdir(parents=True, exist_ok=True)
    with lock(root / 'worker.lock'):
        snapshot = root / 'config.snapshot.json'
        if snapshot.exists() and read(snapshot) != config:
            raise ValueError('Cannot change an existing author history; create a new campaign')
        if (root / 'result.json').exists():
            return read(root / 'result.json')
        if (root / 'dispatch.json').exists():
            raise RuntimeError('Existing dispatch: inspect receipts; never blindly replay an author request')
        if shutil.disk_usage(root).free < config['minimum_free_bytes']:
            raise RuntimeError('Author job not dispatched: disk reserve would be violated')
        validate_model(config)
        sandbox = Sandbox(**config['sandbox'])
        sandbox.probe()
        if config.get('native_backend', 'local') == 'ssh-slurm':
            from .slurm_runner import SlurmRunner
            runner = SlurmRunner(root / 'native', sandbox, remote=config['remote'])
        elif config.get('native_backend', 'local') == 'local':
            runner = AuthorRunner(root / 'native', sandbox, reserve=config['minimum_free_bytes'])
        else:
            raise ValueError('Unknown native execution backend; no fallback to local')
        harness = Codex(root / 'agent', config, runner, config['public'], config['docs'])
        prompt = Path(job['prompt']).read_text()
        write_once(root / 'config.snapshot.json', config)
        write_once(root / 'dispatch.json', {
            'pid': os.getpid(), 'started': datetime.now(timezone.utc).isoformat(),
            'job': job_id, 'model': config['model'],
            'account_home': config['harness']['auth_home'],
            'purpose': 'reference_authoring_not_scored_evaluation',
        })
        try:
            result = harness.run(prompt, config['budget']['model_calls'])
        except BaseException as exc:
            write_once(root / 'interrupted.json', {'type': type(exc).__name__, 'message': str(exc)})
            raise
        outputs = {name: (harness.work / name).is_file() for name in job['expected_outputs']}
        value = {'job': job_id, 'harness': result, 'outputs_present': outputs,
                 'lifecycle': 'completed', 'release_qualified': False,
                 'note': 'Author output is evidence to validate, not automatic scientific qualification.'}
        write_once(root / 'result.json', value)
        return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    print(__import__('json').dumps(execute(args.config, args.job), ensure_ascii=False), flush=True)
