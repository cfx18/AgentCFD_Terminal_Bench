from copy import deepcopy

import pytest

from agentcfd_bench.authoring.migrate_slurm import freeze
from agentcfd_bench.records.store import read, write_once


def fixture(tmp_path):
    source = tmp_path / 'local'
    source.mkdir()
    prompt = source / 'prompt.md'
    prompt.write_text('Original scientific task.')
    config = {'root': str(source), 'model': 'gpt-5.6-luna', 'author_concurrency': 10,
              'jobs': {'a': {'prompt': str(prompt)}, 'b': {'prompt': str(prompt)}},
              'job_order': ['b', 'a'], 'after_campaign': '/old/pilot', 'budget': {'model_calls': 120},
              'harness': {'auth_home': '/root/.codex-experiment'}}
    write_once(source / 'campaign.json', config)
    write_once(source / 'registry.json', {'candidates': ['all', 'source', 'entries']})
    gate = tmp_path / 'gate'
    write_once(gate / 'gate-ready.json', {'source_config': str(source / 'campaign.json'),
                                        'unstarted_jobs': ['a'], 'existing_jobs': ['b']})
    write_once(gate / 'drained.json', {'unstarted_jobs': ['a'], 'preserved_existing_jobs': ['b']})
    prefix = '/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/test'
    remote = {'host': 'sca2070', 'root': prefix + '/operations', 'partition': 'amd_256',
              'runtime': '/runtime', 'python': '/python', 'apptainer': '/apptainer', 'image': '/image',
              'runtime_manifest_sha256': 'verified',
              'pool': {'root': prefix + '/production', 'operations': prefix + '/operations',
                       'allocation_cpus': 64, 'max_parallel': 10, 'step_cpus': 1}}
    write_once(tmp_path / 'remote.json', remote)
    proof = {'passed': True, 'peak_parallel': 10, 'native': {'passed': True}, 'remote': deepcopy(remote)}
    proof['remote']['pool']['root'] = prefix + '/probe'
    write_once(tmp_path / 'proof.json', proof)
    return [source / 'campaign.json', gate, tmp_path / 'remote.json', tmp_path / 'proof.json', tmp_path / 'new']


def test_migrate_preserves_tasks_history_account_and_budgets(tmp_path):
    args = fixture(tmp_path)
    before = args[0].read_bytes()
    result = freeze(*args)
    config = read(result['config'])
    assert config['job_order'] == ['a'] and config['migration']['preserved_local_jobs'] == ['b']
    assert config['budget']['model_calls'] == 120
    assert config['harness']['auth_home'] == '/root/.codex-experiment'
    assert 'after_campaign' not in config and config['after_receipt'].endswith('drained.json')
    assert args[0].read_bytes() == before
    assert read(args[-1] / 'registry.json')['candidates'] == ['all', 'source', 'entries']
    assert 'Original scientific task.' in (args[-1] / 'prompts/a.md').read_text()


def test_migration_refuses_dispatched_work(tmp_path):
    args = fixture(tmp_path)
    write_once(args[0].parent / 'workers/a/dispatch.json', {'already': 'dispatched'})
    with pytest.raises(ValueError, match='replay'):
        freeze(*args)
    assert not args[-1].exists()


def test_migration_refuses_failed_qualification(tmp_path):
    args = fixture(tmp_path)
    args[3].write_text('{"passed": false}')
    with pytest.raises(ValueError, match='qualification'):
        freeze(*args)
    assert not args[-1].exists()


def test_migration_never_reuses_stopped_probe_pool(tmp_path):
    args = fixture(tmp_path)
    proof = read(args[3])
    proof['remote'] = read(args[2])
    args[3].write_text(__import__('json').dumps(proof))
    with pytest.raises(ValueError, match='fresh pool'):
        freeze(*args)


def test_retirement_waits_for_model_and_only_signals_controller(tmp_path, monkeypatch):
    from agentcfd_bench.authoring import migration_gate as gate_module
    args = fixture(tmp_path)
    identity = {'state': 'S', 'ticks': '123',
                'command': 'agentcfd_bench.authoring.control supervise ' + str(args[0])}
    gate = read(args[1] / 'gate-ready.json')
    gate.update(controller_pid=12345, controller_identity=identity)
    (args[1] / 'gate-ready.json').write_text(__import__('json').dumps(gate))
    monkeypatch.setattr(gate_module, 'process_identity', lambda pid: identity)
    killed = []
    monkeypatch.setattr(gate_module.os, 'kill', lambda pid, sig: killed.append(pid))
    with pytest.raises(RuntimeError, match='still active'):
        gate_module.retire_finished_authors(args[0], args[1])
    assert killed == []
    worker = args[0].parent / 'workers/b'
    write_once(worker / 'result.json', {'author': 'ended'})
    write_once(worker / 'native/r-test/dispatch.json', {'state': 'intent'})
    write_once(worker / 'native/r-test/worker.json', {'pid': 45678})
    result = gate_module.retire_finished_authors(args[0], args[1])
    assert killed == [12345] and result['native_jobs_cancelled'] is False
    assert result['native_workers_preserved'][0]['worker']['pid'] == 45678


def test_retirement_refuses_reused_controller_pid(tmp_path, monkeypatch):
    from agentcfd_bench.authoring import migration_gate as gate_module
    args = fixture(tmp_path)
    write_once(args[0].parent / 'workers/b/result.json', {})
    gate = read(args[1] / 'gate-ready.json')
    gate.update(controller_pid=12345, controller_identity={'ticks': 'old'})
    (args[1] / 'gate-ready.json').write_text(__import__('json').dumps(gate))
    monkeypatch.setattr(gate_module, 'process_identity', lambda pid: {'state': 'S', 'ticks': 'new'})
    monkeypatch.setattr(gate_module.os, 'kill', lambda *a: pytest.fail('Must not kill reused PID'))
    with pytest.raises(RuntimeError, match='identity changed'):
        gate_module.retire_finished_authors(args[0], args[1])
