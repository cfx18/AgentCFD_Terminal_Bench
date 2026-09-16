"""Fake model + real bounded native process: terminal, interrupted and resume paths."""

from pathlib import Path
import json
import time

import pytest
import yaml

from agentcfd_bench import controller
from agentcfd_bench.tasks.experiment import archive
from agentcfd_bench.records.store import Store, read, write_once
from agentcfd_bench.reports.summary import report, markdown
from agentcfd_bench.execution.identity import runtime_identity

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def runroot(tmp_path, request):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "manual.txt").write_text("offline")
    foam = tmp_path / "foam"
    (foam / "bin").mkdir(parents=True)
    program = foam / "bin/nativeFixture"
    program.write_text('#!/bin/sh\nif [ "$1" = fail ]; then exit 2; fi\n'
                       'if [ "$1" = wait ]; then sleep 0.3; fi\necho End\n')
    program.chmod(0o755)
    write_once(
        foam / "workbench-manifest.json",
        {"fake_test_runtime": True, "content_identity": runtime_identity(foam)},
    )
    config = {
        "version": "workbench-v3",
        "harness": {"name": "codex", "reasoning_effort": "xhigh"},
        "model": "LOCAL_FAKE",
        "tasks": ["s-205"],
        "task_root": str(PROJECT / "tasks/releases/workbench-v3"),
        "docs": str(docs),
        "network": "disabled",
        "execution": {"foam_root": str(foam)},
        "budget": {"model_calls": 3, "native_seconds": 10, "request_seconds": 5},
        "output": str(tmp_path / "runs"),
    }
    path = tmp_path / "experiment.yaml"
    config.update(getattr(request, "param", {}))
    path.write_text(yaml.safe_dump(config))
    return archive(path)


class FakeModel:
    def __init__(self, trial, config, runner, *args):
        self.root = trial
        self.runner = runner

    def run(self, prompt, remaining_calls, session=None):
        work = self.root / "work"
        work.mkdir(exist_ok=True)
        operation = self.runner.start(work, ["nativeFixture"], kind="run")
        until = time.monotonic() + 5
        while self.runner.status(operation["run_id"])["lifecycle"] == "running":
            assert time.monotonic() < until
            time.sleep(0.02)
        write_once(self.root / "submission.json", {"run_id": operation["run_id"]})
        result = {
            "calls": 1,
            "session": "local-fake-session",
            "completed": True,
            "errors": [],
            "exit_code": 0,
        }
        write_once(self.root / "calls/turn-0001/result.json", result)
        return result


@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_terminal_then_resume_does_not_rerun(runroot, monkeypatch, verdict):
    from agentcfd_bench.grading import service

    grades = []

    def grade(*args):
        grades.append(1)
        return {"verdict": verdict, "reason": "fake_physical_acceptance"}

    monkeypatch.setattr(service, "grade_submission", grade)
    value = controller.resume(runroot, agent_class=FakeModel)
    assert value["tasks"][0]["verdict"] == verdict
    assert value["tasks"][0]["calls"] == 1 and value["tasks"][0]["solver_runs"] == 1
    assert (
        controller.resume(runroot, agent_class=FakeModel) == value and len(grades) == 1
    )
    assert markdown(runroot) == markdown(runroot)


def test_unknown_request_stays_interrupted_without_reissue(runroot):
    class Unknown(FakeModel):
        def run(self, *args, **kwargs):
            raise TimeoutError("request outcome unknown")

    first = controller.resume(runroot, agent_class=Unknown)
    assert first["tasks"][0]["reason"] == "model_request_outcome_unresolved"

    class MustNotDispatch(FakeModel):
        def run(self, *args, **kwargs):
            pytest.fail("Unknown API request was replayed")

    again = controller.resume(runroot, agent_class=MustNotDispatch)
    assert again["tasks"][0]["lifecycle"] == "interrupted"
    assert again["errors"] == 1 and not again["rates_are_final"]


def test_known_response_before_state_commit_is_recovered(runroot, monkeypatch):
    from agentcfd_bench.grading import service

    trial = runroot / "trials/s-205"
    state = {
        "lifecycle": "running",
        "verdict": "not_evaluated",
        "calls": 2,
        "session": "same",
        "request_inflight": True,
    }
    Store(trial).set("trial", state)
    write_once(
        trial / "calls/turn-0001/result.json",
        {
            "calls": 1,
            "session": "same",
            "errors": [],
            "completed": True,
            "exit_code": 0,
        },
    )

    class MustNotDispatch(FakeModel):
        def run(self, *args, **kwargs):
            pytest.fail("Call budget was reset")

    value = controller.resume(runroot, agent_class=MustNotDispatch)
    row = value["tasks"][0]
    assert (
        row["calls"] == 3
        and row["reason"] == "model_budget_exhausted"
        and row["verdict"] == "fail"
    )


def test_report_reads_committed_state_not_stale_projection(runroot):
    trial = runroot / "trials/s-205"
    Store(trial).set("trial", {"lifecycle": "completed", "verdict": "pass"})
    (trial / "status.json").write_text(
        '{"lifecycle":"running","verdict":"not_evaluated"}'
    )
    assert report(runroot)["passed"] == 1


def test_dense_budget_exhaustion_persists_zero_reward(runroot, monkeypatch):
    from agentcfd_bench.tasks.loader import Task
    from agentcfd_bench.grading.dense_rubric import approved_rubric
    monkeypatch.setattr(Task, 'private', lambda self: ({}, {
        'policy':'dense-observation-v1','release_status':'released','rubric':approved_rubric('s-203')}))
    Store(runroot / 'trials/s-205').set('trial', {
        'calls':3,'lifecycle':'running','session':None,'request_inflight':False})
    class NeverCalled(FakeModel):
        def run(self, *args, **kwargs):
            pytest.fail('Exhausted model budget must not dispatch')
    value = controller.resume(runroot, agent_class=NeverCalled)
    assert value['mean_reward_scored'] == 0 and value['reward_denominator'] == 1
    assert read(runroot / 'trials/s-205/grading/reward.json')['reward'] == 0


AUTOFINAL = {
    "completion": {"on_model_budget_exhausted": "evaluate_latest_successful"},
    "budget": {"model_calls": 120, "native_seconds": None, "request_seconds": 5},
}


class BudgetModel(FakeModel):
    explicit = False

    def run(self, prompt, remaining_calls, session=None):
        assert remaining_calls == 120
        assert 'Native-time budget is unlimited' in prompt
        assert 'latest successfully exited native run' in prompt
        work = self.root / 'work'
        work.mkdir(exist_ok=True)
        runs = []
        for args, kind in [(['nativeFixture'], 'run'),
                           (['nativeFixture', 'wait'], 'run'),
                           (['nativeFixture', 'fail'], 'run'),
                           (['/bin/true'], 'exec')]:
            operation = self.runner.start(work, args, kind=kind)
            runs.append(operation['run_id'])
            until = time.monotonic() + 5
            while self.runner.status(operation['run_id'])['lifecycle'] == 'running':
                assert time.monotonic() < until
                time.sleep(.02)
        write_once(self.root / 'expected-selection.json', {'run_id': runs[0 if self.explicit else 1]})
        if self.explicit:
            write_once(self.root / 'submission.json', {'run_id': runs[0]})
        # The broker's refusal of call 121 can give the CLI a nonzero exit.
        result = {'calls': 120, 'session': 'same-session', 'completed': False,
                  'errors': [], 'exit_code': 1, 'budget_exhausted': True}
        write_once(self.root / 'calls/turn-0001/result.json', result)
        return result


def cached_fake_grade(task, runner, run_id, output):
    assert runner.verify(run_id)[1]['success']
    expected = read(output.parent / 'expected-selection.json')['run_id']
    assert run_id == expected
    path = output / 'result.json'
    if not path.exists():
        write_once(path, {'verdict': 'fail', 'reason': 'physical_error', 'reward': .5})
    return read(path)


@pytest.mark.parametrize('runroot', [AUTOFINAL], indirect=True)
@pytest.mark.parametrize('explicit', [False, True])
def test_call_cap_grades_native_answer_not_cli_exit(runroot, monkeypatch, explicit):
    from agentcfd_bench.grading import service
    monkeypatch.setattr(service, 'grade_submission', cached_fake_grade)
    class Model(BudgetModel):
        pass
    Model.explicit = explicit
    value = controller.resume(runroot, agent_class=Model)
    row = value['tasks'][0]
    assert row['calls'] == 120 and value['mean_reward_scored'] == .5
    assert row['lifecycle'] == 'completed' and row['reason'] == 'physical_error'
    assert row['stop_reason'] == 'model_budget_exhausted'
    assert row['selection_source'] == ('agent_submission' if explicit else 'budget_fallback')
    trial = runroot / 'trials/s-205'
    summary = read(trial / 'finalization/summary.json')
    assert summary['additional_model_calls'] == 0
    assert summary['grading']['reward'] == .5
    assert (trial / 'submission.json').exists() == explicit  # Never impersonate Agent.
    monkeypatch.setattr(service, 'grade_submission', lambda *a: pytest.fail('Already graded'))
    assert controller.resume(runroot, agent_class=Model) == value


@pytest.mark.parametrize('runroot', [AUTOFINAL], indirect=True)
def test_budget_result_before_state_commit_is_recovered(runroot, monkeypatch):
    from agentcfd_bench.grading import service
    from agentcfd_bench import finalization
    monkeypatch.setattr(service, 'grade_submission', cached_fake_grade)
    original = finalization.record_summary
    def interrupt(*args):
        raise KeyboardInterrupt
    monkeypatch.setattr(finalization, 'record_summary', interrupt)
    with pytest.raises(KeyboardInterrupt):
        controller.resume(runroot, agent_class=BudgetModel)
    trial = runroot / 'trials/s-205'
    assert (trial / 'grading/result.json').exists()
    assert Store(trial).get('trial')['phase'] == 'finalizing'
    monkeypatch.setattr(finalization, 'record_summary', original)
    class NoNewModel:
        def __init__(self, *args):
            pytest.fail('No model construction or extra call during recovery')
    value = controller.resume(runroot, agent_class=NoNewModel)
    assert value['mean_reward_scored'] == .5
    assert value['tasks'][0]['calls'] == 120


@pytest.mark.parametrize('runroot', [AUTOFINAL], indirect=True)
def test_budget_receipt_recovers_after_nonzero_cli_exit(runroot, monkeypatch):
    from agentcfd_bench.grading import service
    from agentcfd_bench.execution.runner import Runner
    from agentcfd_bench.execution.sandbox import Sandbox
    monkeypatch.setattr(service, 'grade_submission', cached_fake_grade)
    trial = runroot / 'trials/s-205'
    config = read(runroot / 'experiment.json')
    runner = Runner(trial / 'native', Sandbox(**config['execution']), seconds=None)
    BudgetModel(trial, config, runner).run(
        'Native-time budget is unlimited; latest successfully exited native run', 120)
    Store(trial).set('trial', {'calls':0, 'lifecycle':'running', 'session':None, 'request_inflight':True})
    class NoDispatch(FakeModel):
        def run(self, *a, **k):
            pytest.fail('Recovered calls must not be resent')
    value = controller.resume(runroot, agent_class=NoDispatch)
    assert value['tasks'][0]['calls'] == 120
    assert value['mean_reward_scored'] == .5


@pytest.mark.parametrize('runroot', [AUTOFINAL], indirect=True)
def test_no_successful_output_has_explicit_reason(runroot):
    trial = runroot / 'trials/s-205'
    Store(trial).set('trial', {'calls':120, 'lifecycle':'running', 'session':None})
    row = controller.resume(runroot, agent_class=FakeModel)['tasks'][0]
    assert row['reason'] == 'no_successful_native_output'
    assert row['selected_run_id'] is None and row['verdict'] == 'fail'
    assert read(trial / 'finalization/summary.json')['additional_model_calls'] == 0


@pytest.mark.parametrize('runroot', [AUTOFINAL], indirect=True)
def test_unknown_budget_request_is_not_graded_or_resent(runroot):
    trial = runroot / 'trials/s-205'
    Store(trial).set('trial', {'calls':120, 'lifecycle':'running', 'session':None, 'request_inflight':True})
    row = controller.resume(runroot, agent_class=FakeModel)['tasks'][0]
    assert row['verdict'] == 'error' and row['reason'] == 'model_request_outcome_unresolved'
    assert not (trial / 'grading/result.json').exists()


@pytest.mark.parametrize('runroot', [AUTOFINAL], indirect=True)
def test_cap_waits_for_dispatched_worker_without_new_model_call(runroot, monkeypatch):
    from agentcfd_bench.grading import service
    monkeypatch.setattr(service, 'grade_submission', cached_fake_grade)
    class StillComputing(FakeModel):
        def run(self, prompt, remaining_calls, session=None):
            work = self.root / 'work'; work.mkdir()
            operation = self.runner.start(work, ['nativeFixture', 'wait'], kind='run')
            assert self.runner.status(operation['run_id'])['lifecycle'] == 'running'
            write_once(self.root / 'expected-selection.json', {'run_id':operation['run_id']})
            result = {'calls':120, 'session':'same', 'completed':False,
                      'errors':[], 'exit_code':1, 'budget_exhausted':True}
            write_once(self.root / 'calls/turn-0001/result.json', result)
            return result
    value = controller.resume(runroot, agent_class=StillComputing)
    assert value['mean_reward_scored'] == .5
    assert value['tasks'][0]['calls'] == 120 and value['tasks'][0]['solver_runs'] == 1
