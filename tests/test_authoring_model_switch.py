from pathlib import Path
import json

import pytest

from agentcfd_bench.authoring import worker, migration_gate, control
from agentcfd_bench.records.store import write_once


def authorized():
    return {'model': 'gpt-5.6-sol',
            'harness': {'auth_home': '/root/.codex-experiment', 'reasoning_effort': 'high'},
            'author_model_authorization': {'model': 'gpt-5.6-sol', 'user_confirmed': True,
                'auth_home': '/root/.codex-experiment', 'reasoning_effort': 'high'}}


def test_exact_authorized_sol_account_and_effort():
    worker.validate_model(authorized())
    worker.validate_model({'model': 'gpt-5.6-luna'})


@pytest.mark.parametrize('key,value', [('model', 'gpt-6-astra'), ('user_confirmed', False),
                                     ('auth_home', '/another-account'), ('reasoning_effort', 'ultra')])
def test_authorization_cannot_be_silently_substituted(key, value):
    config = authorized()
    config['author_model_authorization'][key] = value
    with pytest.raises(ValueError, match='authorized'):
        worker.validate_model(config)


def test_gate_targets_resumed_controller(tmp_path):
    write_once(tmp_path / 'launch.json', {'pid': 1, 'started': '2026-09-16T01:00:00Z'})
    write_once(tmp_path / 'launch.resume-001.json', {'pid': 2, 'started': '2026-09-16T02:00:00Z'})
    assert migration_gate.latest_controller(tmp_path)['pid'] == 2


def test_changed_model_cannot_relabel_existing_results(tmp_path):
    old = {'root': str(tmp_path), 'model': 'gpt-5.6-luna', 'jobs': {'a': {}}}
    write_once(tmp_path / 'workers/a/config.snapshot.json', old)
    write_once(tmp_path / 'workers/a/result.json', {'historical': 'Luna'})
    new = {**old, **authorized()}
    write_once(tmp_path / 'changed.json', new)
    with pytest.raises(ValueError, match='existing author history'):
        worker.execute(tmp_path / 'changed.json', 'a')


def test_superseded_campaign_cannot_restart(tmp_path):
    write_once(tmp_path / 'superseded.json', {'replacement': 'another-campaign'})
    write_once(tmp_path / 'campaign.json', {'root': str(tmp_path)})
    with pytest.raises(RuntimeError, match='superseded'):
        control.launch(tmp_path / 'campaign.json', resume_known=True)


def test_prompt_switch_preserves_scientific_task():
    from agentcfd_bench.authoring.switch_model import adapt_prompt
    prefix = 'Use GPT-5.6 Luna through Codex; do not launch subagents.'
    science = '\nUse the original geometry and boundary conditions. No shortcuts.'
    assert adapt_prompt(prefix + science) == prefix.replace('Luna', 'Sol') + science
    with pytest.raises(ValueError, match='identity'):
        adapt_prompt('No known author identity')


def switch_fixture(tmp_path, monkeypatch):
    from agentcfd_bench.authoring import switch_model
    source = tmp_path / 'source'
    prompt = tmp_path / 'prompt.md'
    prompt.write_text('Use GPT-5.6 Luna through Codex; do not launch subagents.\nScience.')
    remote = {'runtime_manifest_sha256': 'same', 'pool': {'root': '/old'}}
    config = {'root': str(source), 'model': 'gpt-5.6-luna', 'harness': {'auth_home': '/root/.codex-experiment'},
              'remote': remote, 'budget': {'model_calls': 120}, 'jobs': {
                  'a': {'prompt': str(prompt), 'expected_outputs': ['author-result.json']},
                  'b': {'prompt': str(prompt), 'expected_outputs': ['author-result.json']}}, 'job_order': ['b', 'a']}
    write_once(source / 'campaign.json', config)
    write_once(source / 'registry.json', {'all_sources': [1, 2, 3]})
    write_once(source / 'launch.resume-001.json', {'pid': 123, 'started': 'today'})
    write_once(source / 'workers/b/result.json', {'harness': {'calls': 2, 'errors': [{'upstream_result_known': True}]}})
    write_once(source / 'gate/gate-ready.json', {'source_config': str(source / 'campaign.json')})
    write_once(source / 'gate/drained.json', {'retired_controller_pid': 123})
    write_once(tmp_path / 'remote.json', {**remote, 'pool': {'root': '/new'}})
    monkeypatch.setattr(switch_model, 'process_identity', lambda pid: None)
    monkeypatch.setattr(switch_model, 'validate_remote', lambda remote: remote)
    return switch_model, [source / 'campaign.json', source / 'gate', tmp_path / 'remote.json', tmp_path / 'new']


def test_switch_freezes_new_attempts_not_relabels(tmp_path, monkeypatch):
    from agentcfd_bench.records.store import read
    module, args = switch_fixture(tmp_path, monkeypatch)
    old = args[0].read_bytes()
    value = module.freeze(*args)
    assert value['counts'] == {'new_model_attempt': 1, 'not_previously_started': 1}
    config = read(value['config'])
    assert config['model'] == 'gpt-5.6-sol' and config['job_order'] == ['b', 'a']
    assert config['budget']['model_calls'] == 120 and args[0].read_bytes() == old
    assert read(args[-1] / 'registry.json')['all_sources'] == [1, 2, 3]
    assert read(args[0].parent / 'superseded.json')['replacement'] == value['config']


def test_switch_refuses_unknown_request(tmp_path, monkeypatch):
    module, args = switch_fixture(tmp_path, monkeypatch)
    record = args[0].parent / 'workers/b/result.json'
    record.write_text(json.dumps({'harness': {'errors': [{'upstream_result_known': False}]}}))
    with pytest.raises(ValueError, match='Unknown provider outcome'):
        module.freeze(*args)
    assert not args[-1].exists()


def test_switch_cannot_duplicate_same_source(tmp_path, monkeypatch):
    module, args = switch_fixture(tmp_path, monkeypatch)
    module.freeze(*args)
    args[-1] = tmp_path / 'duplicate'
    with pytest.raises(ValueError, match='already switched'):
        module.freeze(*args)
    assert not args[-1].exists()
