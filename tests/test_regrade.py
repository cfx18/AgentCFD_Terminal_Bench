"""A grading correction must not silently replace the model's answer or history."""

import importlib
import json

import pytest

from agentcfd_bench import controller
from agentcfd_bench.grading import service
from agentcfd_bench.records.store import Store, lock, read, write_once
from agentcfd_bench.reports.summary import report, markdown

from test_controller import FakeModel, runroot, BudgetModel, AUTOFINAL, cached_fake_grade

module = importlib.import_module("agentcfd_bench.grading.regrade")


def complete(runroot, monkeypatch):
    def original(task, runner, run_id, root):
        result = {"verdict": "fail", "reason": "old_parser_limit"}
        write_once(root / "result.json", result)
        return result

    monkeypatch.setattr(service, "grade_submission", original)
    controller.resume(runroot, agent_class=FakeModel)
    return runroot / "trials/s-205"


@pytest.mark.parametrize("verdict", ["pass", "fail", "error"])
def test_regrade_preserves_history_and_updates_readonly_report(runroot, monkeypatch, verdict):
    trial = complete(runroot, monkeypatch)
    old = (trial / "grading/result.json").read_bytes()
    submission = (trial / "submission.json").read_bytes()
    prior = Store(trial).get("trial")
    original_native = sorted(p.name for p in (trial / "native").iterdir())

    def corrected(task, runner, run_id, root):
        assert run_id == json.loads(submission)["run_id"]
        result = {"verdict": verdict, "reason": "replayed_same_answer",
                  "reward": 0.7 if verdict == "pass" else None}
        write_once(root / "result.json", result)
        return result

    monkeypatch.setattr(module, "grade_submission", corrected)
    outcome = module.regrade(runroot, "s-205")
    assert outcome["previous_verdict"] == "fail"
    assert (trial / "grading/result.json").read_bytes() == old
    assert (trial / "submission.json").read_bytes() == submission
    assert sorted(p.name for p in (trial / "native").iterdir()) == original_native
    after = Store(trial).get("trial")
    assert after["calls"] == prior["calls"] == 1
    assert after["verdict"] == verdict
    assert read(trial / after["grading_result"])["verdict"] == verdict
    assert report(runroot)["tasks"][0]["reward"] == (0.7 if verdict == "pass" else None)
    assert "重验收记录" in markdown(runroot)
    assert report(runroot) == report(runroot)


def test_cannot_choose_unsubmitted_answer_or_regrade_live_controller(runroot, monkeypatch):
    trial = runroot / "trials/s-205"
    Store(trial).set("trial", {"lifecycle": "completed", "verdict": "fail", "calls": 3})
    with pytest.raises(ValueError, match="No explicit submission"):
        module.regrade(runroot, "s-205")
    with lock(runroot / "controller.lock"):
        with pytest.raises(RuntimeError, match="controller"):
            module.regrade(runroot, "s-205")
    assert not (trial / "regrades").exists()


def test_incomplete_regrade_receipt_does_not_publish_score(runroot, monkeypatch):
    trial = complete(runroot, monkeypatch)
    before = Store(trial).get("trial")

    def crash(*args):
        raise RuntimeError("export interrupted")

    monkeypatch.setattr(module, "grade_submission", crash)
    with pytest.raises(RuntimeError, match="export interrupted"):
        module.regrade(runroot, "s-205")
    assert Store(trial).get("trial") == before
    assert len(list((trial / "regrades").glob("*/intent.json"))) == 1
    assert not list((trial / "regrades").glob("*/commit.json"))


def test_evidence_tampering_is_rejected_before_regrading(runroot, monkeypatch):
    trial = complete(runroot, monkeypatch)
    run_id = read(trial / "submission.json")["run_id"]
    (trial / "native" / run_id / "stdout.log").write_text("fabricated End\n")
    with pytest.raises(RuntimeError, match="evidence changed"):
        module.regrade(runroot, "s-205")
    assert not (trial / "regrades").exists()


@pytest.mark.parametrize('runroot', [AUTOFINAL], indirect=True)
def test_regrade_reuses_frozen_fallback_never_selects_another_answer(runroot, monkeypatch):
    monkeypatch.setattr(service, 'grade_submission', cached_fake_grade)
    controller.resume(runroot, agent_class=BudgetModel)
    trial = runroot / 'trials/s-205'
    original = read(trial / 'finalization/selection.json')
    def corrected(task, runner, run_id, root):
        assert run_id == original['run_id']
        result = {'verdict':'pass', 'reason':'corrected_export', 'reward':1}
        write_once(root / 'result.json', result)
        return result
    monkeypatch.setattr(module, 'grade_submission', corrected)
    assert module.regrade(runroot, 's-205')['result']['reward'] == 1
    assert read(trial / 'finalization/selection.json') == original
    assert read(trial / 'grading/result.json')['reward'] == .5
    assert not (trial / 'submission.json').exists()
