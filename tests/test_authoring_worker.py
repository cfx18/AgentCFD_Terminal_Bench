import json
from pathlib import Path

import pytest

from agentcfd_bench.authoring import worker, prepare, control
from agentcfd_bench.records.store import write_once


def configuration(tmp_path):
    prompt = tmp_path / 'prompt.md'
    prompt.write_text('AUTHOR, not contestant')
    config = {'root': str(tmp_path / 'campaign'), 'model': 'gpt-5.6-luna',
              'harness': {'auth_home': '/not-a-real-account'},
              'budget': {'model_calls': 120}, 'minimum_free_bytes': 0,
              'public': str(tmp_path), 'docs': str(tmp_path), 'sandbox': {},
              'target_qualified_tasks': 100, 'jobs': {
                  'q-0001': {'prompt': str(prompt), 'expected_outputs': ['author-result.json']}}}
    path = tmp_path / 'config.json'
    write_once(path, config)
    return path, config


def test_mock_author_never_automatically_qualifies(tmp_path, monkeypatch):
    path, config = configuration(tmp_path)
    calls = []
    monkeypatch.setattr(worker.Sandbox, 'probe', lambda self: {})
    class Fake:
        def __init__(self, root, config, runner, public, docs):
            self.work = root / 'work'
            self.work.mkdir(parents=True)
        def run(self, prompt, remaining_calls):
            calls.append((prompt, remaining_calls))
            (self.work / 'author-result.json').write_text('{}')
            return {'calls': 2, 'completed': True}
    monkeypatch.setattr(worker, 'Codex', Fake)
    result = worker.execute(path, 'q-0001')
    assert result['outputs_present'] == {'author-result.json': True}
    assert result['release_qualified'] is False
    assert worker.execute(path, 'q-0001') == result
    assert len(calls) == 1
    assert control.status(path)['workers']['q-0001']['model_calls'] == 2


def test_ambiguous_dispatch_not_repeated(tmp_path):
    path, config = configuration(tmp_path)
    write_once(Path(config['root']) / 'workers/q-0001/dispatch.json', {'pid': 999999999})
    with pytest.raises(RuntimeError, match='never blindly replay'):
        worker.execute(path, 'q-0001')
    assert control.status(path)['workers']['q-0001']['lifecycle'] == 'interrupted'


def test_no_other_model_or_account_substitution(tmp_path):
    path, config = configuration(tmp_path)
    config['model'] = 'another-model'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match='authorized'):
        worker.execute(path, 'q-0001')


def test_source_identity_before_extraction(tmp_path):
    archive = tmp_path / 'fake.tgz'
    archive.write_bytes(b'not original')
    config = tmp_path / 'config.json'
    write_once(config, {'archive': str(archive)})
    with pytest.raises(ValueError, match='identity mismatch'):
        prepare.prepare(config, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_detached_command_uses_importable_module(tmp_path, monkeypatch):
    path, config = configuration(tmp_path)
    Path(config['root']).mkdir()
    argv = []
    class Child:
        pid = 1234567
    def spawn(command, **kwargs):
        argv.extend(command)
        assert kwargs['start_new_session'] is True
        return Child()
    monkeypatch.setattr(control.subprocess, 'Popen', spawn)
    monkeypatch.setattr(control, '__name__', '__main__')
    control.launch(path)
    assert argv[2] == 'agentcfd_bench.authoring.control'
    with pytest.raises(RuntimeError, match='already launched'):
        control.launch(path)


def test_batches_ten_preserve_frozen_order():
    order = [f'q-{i:04d}' for i in range(24, 0, -1)]
    config = {'job_order': order, 'jobs': {x: {} for x in sorted(order)}, 'author_concurrency': 10}
    groups = control.batches(config)
    assert [len(x) for x in groups] == [10, 10, 4]
    assert [x for group in groups for x in group] == order
    config['job_order'] = order + order[:1]
    with pytest.raises(ValueError, match='exactly once'):
        control.batches(config)


def test_unknown_provider_result_is_infra_error_not_plain_completed(tmp_path):
    path, config = configuration(tmp_path)
    worker_root = Path(config['root']) / 'workers/q-0001'
    write_once(worker_root / 'result.json', {
        'harness': {'calls': 7, 'errors': [{'type': 'RemoteProtocolError', 'upstream_result_known': False}]},
        'outputs_present': {'author-result.json': False}})
    state = control.status(path)['workers']['q-0001']
    assert state['lifecycle'] == 'infra_error'
    assert state['infrastructure_error']['reason'] == 'provider_result_unknown'
    assert control.terminal_author(config, 'q-0001')


def test_unknown_provider_after_outputs_is_reviewable_interface_error(tmp_path):
    path, config = configuration(tmp_path)
    worker_root = Path(config['root']) / 'workers/q-0001'
    write_once(worker_root / 'result.json', {
        'harness': {'calls': 7, 'errors': [{'type': 'RemoteProtocolError', 'upstream_result_known': False}]},
        'outputs_present': {'author-result.json': True}})
    state = control.status(path)['workers']['q-0001']
    assert state['lifecycle'] == 'completed_with_interface_error'
    assert state['infrastructure_error']['retryable'] is False


def test_recover_infra_freezes_independent_retry_campaign(tmp_path):
    from agentcfd_bench.authoring import recover_infra
    from agentcfd_bench.records.store import read
    path, config = configuration(tmp_path)
    source_root = Path(config['root'])
    write_once(source_root / 'registry.json', {'all_sources': ['kept']})
    write_once(source_root / 'workers/q-0001/result.json', {
        'harness': {'calls': 7, 'errors': [{'type': 'RemoteProtocolError', 'upstream_result_known': False}]},
        'outputs_present': {'author-result.json': False}})
    output = tmp_path / 'retry'
    value = recover_infra.freeze(path, output)
    retry = read(value['config'])
    assert value['jobs'] == ['q-0001']
    assert retry['root'] == str(output.resolve())
    assert retry['jobs']['q-0001']['prompt'].startswith(str(output.resolve()))
    assert Path(retry['jobs']['q-0001']['prompt']).read_text() == 'AUTHOR, not contestant'
    assert read(output / 'registry.json') == {'all_sources': ['kept']}
