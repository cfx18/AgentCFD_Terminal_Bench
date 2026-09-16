from pathlib import Path

import pytest

from agentcfd_bench import launch
from agentcfd_bench.records.store import write_once, digest


def setup(monkeypatch, tmp_path):
    config = {'output':str(tmp_path),'model':'LOCAL_FAKE'}
    monkeypatch.setattr(launch, 'load', lambda _: (config, []))
    monkeypatch.setattr(launch.subprocess, 'Popen', lambda *a, **k: pytest.fail('Must not dispatch'))
    return config


def test_blocked_preparation_never_dispatches(tmp_path, monkeypatch):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr(launch, 'prepare', lambda _: {'ready':False,'blockers':['rubric missing']})
    with pytest.raises(RuntimeError, match='Preparation blocked'):
        launch.launch('unused.yaml')


def test_repeated_launch_returns_existing_live_process(tmp_path, monkeypatch):
    config = setup(monkeypatch, tmp_path)
    write_once(tmp_path / 'run/launch-intent.json', {'config_identity':digest(config)})
    write_once(tmp_path / 'run/launch.json', {'pid':123})
    monkeypatch.setattr(launch, 'alive', lambda _: True)
    assert launch.launch('unused.yaml')['already_running']


def test_unknown_detached_dispatch_is_not_replayed(tmp_path, monkeypatch):
    config = setup(monkeypatch, tmp_path)
    write_once(tmp_path / 'run/launch-intent.json', {'config_identity':digest(config)})
    with pytest.raises(RuntimeError, match='outcome unknown'):
        launch.launch('unused.yaml')
