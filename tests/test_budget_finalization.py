"""No paid API: unlimited workers, deterministic selection and recovery evidence."""

from pathlib import Path
from types import SimpleNamespace
import time

import pytest
import yaml

from agentcfd_bench import finalization
from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.harnesses.codex import Codex
from agentcfd_bench.harnesses.kimi import KimiCode
from agentcfd_bench.records.store import read, write_once
from agentcfd_bench.tasks.experiment import load


def wait(runner, operation):
    until = time.monotonic() + 5
    while True:
        result = runner.status(operation['run_id'])
        if result['lifecycle'] != 'running':
            return result
        assert time.monotonic() < until
        time.sleep(.02)


@pytest.mark.parametrize('bridge', [Codex, KimiCode])
def test_unlimited_removes_whole_cli_timeout_not_api_watchdog(bridge):
    model = object.__new__(bridge)
    model.config = {'budget': {'request_seconds': 600}}
    model.runner = SimpleNamespace(remaining=lambda: None)
    assert model.client_timeout(120) is None
    assert model.config['budget']['request_seconds'] == 600
    model.runner = SimpleNamespace(remaining=lambda: 10)
    assert model.client_timeout(3) == 2050


def test_unlimited_real_native_process_and_manual_cancel(tmp_path):
    work = tmp_path / 'work'; work.mkdir()
    runner = Runner(tmp_path / 'native', Sandbox(), seconds=None)
    operation = runner.start(work, ['/bin/sh', '-c', 'echo saved > T; sleep .3'])
    root = runner.directory(operation['run_id'])
    assert read(root / 'spec.json')['seconds'] is None
    assert operation['seconds_reserved'] is None
    assert wait(runner, operation)['success']
    assert runner.remaining() is None
    pending = runner.start(work, ['/bin/sleep', '10'])
    assert read(runner.directory(pending['run_id']) / 'dispatch.json')['sequence'] == 2
    runner.cancel(pending['run_id'])
    assert wait(runner, pending)['termination'] == 'cancelled'
    assert Runner(runner.root, Sandbox(), seconds=None).remaining() is None
    with pytest.raises(ValueError, match='changed runtime'):
        Runner(runner.root, Sandbox(), seconds=1000)


def test_agent_can_still_request_individual_command_timeout(tmp_path):
    work = tmp_path / 'work'; work.mkdir()
    runner = Runner(tmp_path / 'native', Sandbox(), seconds=None)
    run = runner.start(work, ['/bin/sleep', '10'], seconds=.1)
    assert wait(runner, run)['termination'] == 'budget_exhausted'
    assert runner.remaining() is None


@pytest.mark.parametrize('invalid', [-1, 0, True, float('inf'), float('nan'), 'unlimited'])
def test_invalid_runtime_is_not_silently_unlimited(tmp_path, invalid):
    with pytest.raises(ValueError):
        Runner(tmp_path / 'native', Sandbox(), seconds=invalid)
    runner = Runner(tmp_path / 'native', Sandbox(), seconds=None)
    with pytest.raises(ValueError):
        runner.start(tmp_path, ['/bin/true'], seconds=invalid)


def fixture_exit(runner, index, *, success=True, kind='run', known_exit=True):
    root = runner.root / f'r-{index:016x}'
    (root / 'case').mkdir(parents=True)
    (root / 'case/T').write_text('recorded native field')
    (root / 'stdout.log').write_text('End\n')
    (root / 'stderr.log').write_text('')
    write_once(root / 'spec.json', {'kind':kind, 'seconds':None})
    write_once(root / 'dispatch.json', {'state':'dispatch_intent', 'sequence':index})
    if known_exit:
        write_once(root / 'exit.json', {'exit_code':0 if success else 2,
                    'termination':'exited', 'elapsed_seconds':.1})
    return root


def test_collect_exit_before_logs_no_execution_and_stable_selection(tmp_path):
    runner = Runner(tmp_path / 'native', Sandbox(), seconds=None)
    earlier = fixture_exit(runner, 1)
    chosen = fixture_exit(runner, 2)
    fixture_exit(runner, 3, success=False)
    fixture_exit(runner, 4, kind='exec')
    assert not (chosen / 'result.json').exists()
    selection = finalization.select(tmp_path, runner)
    assert selection['run_id'] == chosen.name
    assert (chosen / 'result.json').exists()
    # Receipt survives controller interruption; do not rerun/reselect by GT.
    assert finalization.select(tmp_path, runner) == selection
    assert all(not (p / 'worker.json').exists() for p in (earlier, chosen))


def test_running_native_work_is_observed_not_replaced(tmp_path, monkeypatch):
    runner = Runner(tmp_path / 'native', Sandbox(), seconds=None)
    chosen = fixture_exit(runner, 1)
    original = runner.status
    calls = []
    def status(run_id):
        calls.append(run_id)
        if len(calls) == 1:
            return {'lifecycle':'running'}
        return original(run_id)
    monkeypatch.setattr(runner, 'status', status)
    monkeypatch.setattr(runner, 'start', lambda *a, **k: pytest.fail('No redispatch'))
    assert finalization.select(tmp_path, runner)['run_id'] == chosen.name
    assert len(calls) >= 2


@pytest.mark.parametrize('missing_exit', [False, True])
def test_missing_or_tampered_evidence_is_not_replaced_by_older_result(tmp_path, missing_exit):
    runner = Runner(tmp_path / 'native', Sandbox(), seconds=None)
    fixture_exit(runner, 1)
    latest = fixture_exit(runner, 2, known_exit=not missing_exit)
    if not missing_exit:
        runner.status(latest.name)
        (latest / 'artifacts/T').write_text('changed')
    with pytest.raises(RuntimeError, match='unresolved|changed'):
        finalization.select(tmp_path, runner)
    assert not (tmp_path / 'finalization/selection.json').exists()


def test_load_explicit_unlimited_and_reject_unknown_policy(tmp_path):
    project = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((project / 'experiments/dense-reconstruction-astra.yaml').read_text())
    for key in ('task_root', 'docs', 'output'):
        config[key] = str((project / 'experiments' / config[key]).resolve())
    config['budget'].update(model_calls=120, native_seconds=None)
    config['completion'] = {'on_model_budget_exhausted':finalization.POLICY}
    path = tmp_path / 'test.yaml'; path.write_text(yaml.safe_dump(config))
    assert load(path)[0]['budget']['native_seconds'] is None
    config['completion']['on_model_budget_exhausted'] = 'best_gt_score'
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='Unknown completion'):
        load(path)
