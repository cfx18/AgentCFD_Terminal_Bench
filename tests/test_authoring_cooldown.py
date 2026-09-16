import json

import pytest

from agentcfd_bench.authoring import control
from agentcfd_bench.records.store import read, write_once


def fixture(tmp_path, code='server_is_overloaded'):
    config = {'root': str(tmp_path), 'jobs': {'a': {}}, 'author_concurrency': 10}
    path = tmp_path / 'campaign.json'
    write_once(path, config)
    worker = tmp_path / 'workers/a'
    write_once(worker / 'result.json', {'harness': {'errors': [{'reason': 'provider_response_failed'}]}})
    response = worker / 'agent/calls/turn-0001/api/call-001/response.raw'
    response.parent.mkdir(parents=True)
    response.write_text('data: ' + json.dumps({'type': 'response.failed', 'response': {'error': {'code': code}}}) + '\n\n')
    return config, path


def test_cooldown_requires_explicit_provider_overload(tmp_path):
    config, _ = fixture(tmp_path, code='another_error')
    assert control.overloaded_jobs(config, ['a']) == []
    assert control.terminal_author(config, 'a')


def test_cooldown_is_durable_and_never_replays_requests(tmp_path, monkeypatch):
    config, path = fixture(tmp_path)
    assert control.overloaded_jobs(config, ['a']) == ['a']
    clock = [1000.0]
    events = []
    monkeypatch.setattr(control.time, 'time', lambda: clock[0])
    monkeypatch.setattr(control.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(control.time, 'sleep', lambda n: clock.__setitem__(0, clock[0] + n))
    monkeypatch.setattr(control, 'progress', lambda *a, **kw: events.append(kw))
    control.cooldown(path, 1, ['a'])
    receipt = read(tmp_path / 'cooldowns/batch-001.json')
    assert clock[0] == 1600 and not receipt['replays_previous_requests']
    assert len(events) >= 2
    control.cooldown(path, 1, ['a'])
    assert clock[0] == 1600  # Restart does not reset the wait or retry an old model request.


def test_resume_refuses_unknown_inflight_author_request(tmp_path, monkeypatch):
    from agentcfd_bench.authoring import migration_gate
    config, path = fixture(tmp_path)
    (tmp_path / 'workers/a/result.json').unlink()
    write_once(tmp_path / 'workers/a/dispatch.json', {})
    write_once(tmp_path / 'launch.json', {'pid': 12345})
    monkeypatch.setattr(migration_gate, 'process_identity', lambda pid: None)
    with pytest.raises(RuntimeError, match='Unresolved author request'):
        control.launch(path, resume_known=True)
