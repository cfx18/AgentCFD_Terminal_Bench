"""Historical native evidence is read only. No new solver or model calls."""

import copy
from pathlib import Path
import json

import pytest

from agentcfd_bench.grading.evaluate import evaluate
from agentcfd_bench.grading.physics.accepted_reference import compare
from agentcfd_bench.tasks.loader import Task

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=["s-202", "s-203", "s-204", "s-205"])
def task(request):
    return Task.load(PROJECT / "tasks/releases/workbench-v3" / request.param)


def test_gt_identical_and_bad_field_rejected(task):
    target, _ = task.private()
    old = json.loads(
        (
            PROJECT
            / "tasks/releases/expert-output-v1"
            / task.task_id
            / "solution/accepted-target.json"
        ).read_text()
    )
    assert target == old
    truth = target["observations"]
    assert compare(task.task_id, truth, truth)[0]
    bad = copy.deepcopy(truth)
    if task.task_id in ("s-202", "s-203"):
        for bins in bad["spatial_volumes"].values():
            for row in bins.values():
                row["T"] += 100
    else:
        key = "T_x_bin_mean" if task.task_id == "s-204" else "p_axial_bin_mean"
        bad["measurements"][key]["value"] = [
            v + 1e6 for v in bad["measurements"][key]["value"]
        ]
    assert not compare(task.task_id, bad, truth)[0]


def native_artifacts(source):
    path = Path(source)
    result = json.loads((path / "result.json").read_text())["payload"]
    artifacts = result["artifacts"]
    # Later trusted exports are append-only author evidence, never inferred data.
    return artifacts


def test_selected_reference_replay(task):
    target, _ = task.private()
    artifacts = native_artifacts(target["source"]["run_directory"])
    score = evaluate(task.task_id, artifacts, target, native_success=True)
    assert score["verdict"] == "pass", score
    assert score["convergence_certified"] is False


def test_zero_exit_without_fields_never_passes(task):
    target, _ = task.private()
    score = evaluate(
        task.task_id, {"solver.log": "Time = 1.5\nEnd\n"}, target, native_success=True
    )
    assert score["verdict"] == "fail", score


def test_failed_native_never_compares(task):
    target, _ = task.private()
    score = evaluate(task.task_id, {}, target, native_success=False)
    assert score["verdict"] == "fail" and score["reason"] == "native_run_not_completed"
