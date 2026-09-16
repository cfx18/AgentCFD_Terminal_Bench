"""Draft grading distinguishes answer errors, infrastructure errors and interruption."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentcfd_bench.grading import dense_native
from agentcfd_bench.records.store import read
from agentcfd_bench.tasks.loader import Task

ROOT = Path(__file__).resolve().parents[1]


def fixture(tmp_path, *, success=True, kind='run'):
    task = Task.load(ROOT / 'task-drafts/dense-observation-v1/s-203')
    native = tmp_path / 'native'
    (native / 'artifacts').mkdir(parents=True)
    state = {'kind': kind, 'success': success, 'artifacts': {'evidence': 'immutable-fixture'}}
    runner = SimpleNamespace(verify=lambda _: (native, state), sandbox=None)
    return task, runner, state


def test_failed_native_run_does_not_sample(tmp_path, monkeypatch):
    task, runner, _ = fixture(tmp_path, success=False)
    monkeypatch.setattr(dense_native, 'sample_case', lambda *a: pytest.fail('Must not sample failed run'))
    value = dense_native.grade(task, runner, 'r-1', tmp_path / 'grade')
    assert value['verdict'] == 'fail' and value['reason'] == 'native_run_not_completed'


@pytest.mark.parametrize('error,verdict,reason', [
    (dense_native.InvalidNativeFields('missing observation points'), 'fail', 'native_observation_invalid'),
    (RuntimeError('Sampling dispatch outcome unknown; do not replay'), 'error', 'dense_sampling_infrastructure_error'),
])
def test_candidate_and_infrastructure_failures_are_separate(tmp_path, monkeypatch, error, verdict, reason):
    task, runner, _ = fixture(tmp_path)
    def failing(*args):
        raise error
    monkeypatch.setattr(dense_native, 'sample_case', failing)
    value = dense_native.grade(task, runner, 'r-1', tmp_path / 'grade')
    assert value['verdict'] == verdict and value['reason'] == reason
    assert read(tmp_path / 'grade/result.json') == value


def test_controller_interruption_preserves_binding_and_resumes_sampler(tmp_path, monkeypatch):
    task, runner, _ = fixture(tmp_path)
    calls = []
    def interrupted(*args):
        calls.append(args[-1])
        raise KeyboardInterrupt
    monkeypatch.setattr(dense_native, 'sample_case', interrupted)
    with pytest.raises(KeyboardInterrupt):
        dense_native.grade(task, runner, 'r-1', tmp_path / 'grade')
    assert (tmp_path / 'grade/submission-binding.json').is_file()
    assert not (tmp_path / 'grade/result.json').exists()
    expected = {'verdict': 'not_evaluated', 'reward': None, 'metric_status': 'completed'}
    def recovered(*args):
        calls.append(args[-1])
        return expected
    monkeypatch.setattr(dense_native, 'sample_case', recovered)
    assert dense_native.grade(task, runner, 'r-1', tmp_path / 'grade') == expected
    assert calls[0] == calls[1]  # resume the same sampler directory, not a new run
    monkeypatch.setattr(dense_native, 'sample_case', lambda *a: pytest.fail('Do not repeat completed grading'))
    assert dense_native.grade(task, runner, 'r-1', tmp_path / 'grade') == expected


def test_different_submission_cannot_reuse_score(tmp_path, monkeypatch):
    task, runner, _ = fixture(tmp_path)
    monkeypatch.setattr(dense_native, 'sample_case', lambda *a: {'verdict': 'not_evaluated', 'reward': None})
    dense_native.grade(task, runner, 'r-1', tmp_path / 'grade')
    with pytest.raises(ValueError, match='another submission'):
        dense_native.grade(task, runner, 'r-2', tmp_path / 'grade')


def test_exec_cannot_be_submitted_as_native_calculation(tmp_path):
    task, runner, _ = fixture(tmp_path, kind='exec')
    with pytest.raises(ValueError, match='native run'):
        dense_native.grade(task, runner, 'r-1', tmp_path / 'grade')
