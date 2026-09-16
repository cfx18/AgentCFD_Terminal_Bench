import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentcfd_bench.authoring import slurm_pool as pool


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(pool, 'scoped', lambda p: Path(p))
    root = tmp_path / 'pool'
    root.mkdir()
    (root / 'queue').mkdir()
    (root / 'done').mkdir()
    settings = {'identity': '0123456789abcdef', 'operations': str(tmp_path / 'ops'), 'partition': 'amd_256',
                'max_parallel': 10, 'orphan_idle_seconds': 1800}
    pool.save(root / 'settings.json', settings)
    return root, settings


def test_ten_operations_share_one_sbatch(tmp_path, monkeypatch):
    root, settings = setup(tmp_path, monkeypatch)
    calls = []
    def fake(argv):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout='13579\n', stderr='')
    monkeypatch.setattr(pool, 'run_command', fake)
    operations = []
    for i in range(10):
        op = Path(settings['operations']) / ('r-' + format(i, '016x'))
        op.mkdir(parents=True)
        pool.save(op / 'uploaded.json', {'uploaded': True})
        operations.append(op)
        assert pool.enqueue(root, op)['job_id'] == '13579'
    assert len(calls) == 1 and calls[0][0] == 'sbatch'
    assert '--nodes=1' in calls[0] and '--ntasks=64' in calls[0]
    assert len(list((root / 'queue').glob('*.json'))) == 10
    assert pool.enqueue(root, operations[0])['job_id'] == '13579'
    assert len(calls) == 1


def test_step_requests_one_exact_cpu_not_another_node():
    argv = pool.step_command('12345', Path('/operation'))
    assert argv[0] == 'srun' and '--jobid=12345' in argv
    assert '--exclusive' in argv and '--exact' in argv
    assert '--nodes=1' in argv and '--ntasks=1' in argv and '--cpus-per-task=1' in argv
    assert 'sbatch' not in argv


def test_closed_pool_cannot_accept_another_operation(tmp_path, monkeypatch):
    root, settings = setup(tmp_path, monkeypatch)
    pool.control(root, 'stop')
    op = Path(settings['operations']) / 'r-0123456789abcdef'
    with pytest.raises(RuntimeError, match='closed'):
        pool.enqueue(root, op)


def test_lost_allocation_receipt_is_discovered_not_resent(tmp_path, monkeypatch):
    root, settings = setup(tmp_path, monkeypatch)
    pool.save(root / 'allocation-intent.json', {'requested': True})
    calls = []
    def fake(argv):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout='24680|acfd-pool-0123456789abcdef\n', stderr='')
    monkeypatch.setattr(pool, 'run_command', fake)
    record = pool.acquire(root, settings)
    assert record['job_id'] == '24680' and record['recovered']
    assert [x[0] for x in calls] == ['squeue', 'sacct']


def test_missing_unknown_allocation_never_creates_new_job(tmp_path, monkeypatch):
    root, settings = setup(tmp_path, monkeypatch)
    pool.save(root / 'allocation-intent.json', {})
    monkeypatch.setattr(pool, 'run_command', lambda argv: SimpleNamespace(returncode=0, stdout='', stderr=''))
    with pytest.raises(RuntimeError, match='refusing duplicate'):
        pool.acquire(root, settings)
