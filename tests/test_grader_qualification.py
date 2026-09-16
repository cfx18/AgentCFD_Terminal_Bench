import copy
from types import SimpleNamespace
import pytest

from agentcfd_bench.grading.qualification import validate, grader_identity
from agentcfd_bench.grading.observations import VERSION
from agentcfd_bench.records.store import write_once, digest


@pytest.mark.parametrize("mutation", ["none", "reference", "code", "tests"])
def test_readiness_requires_bound_test_evidence(tmp_path, mutation):
    target = {"observation_version": VERSION, "value": 1}
    proof = {
        "grader_identity": grader_identity(),
        "reference_identity": digest(target),
        "task_id": "fixture",
        "reference_replay": "pass",
        "corrupt_field_rejected": True,
        "regression_tests_passed": True,
    }
    if mutation == "code":
        proof["grader_identity"] = "old-code"
    if mutation == "tests":
        proof["regression_tests_passed"] = False
    if mutation == "reference":
        target["value"] = 2
    write_once(tmp_path / "private/qualification.json", proof)
    task = SimpleNamespace(root=tmp_path, task_id="fixture")
    policy = {"observation_version": VERSION, "general_mesh_qualified": True}
    if mutation == "none":
        validate(task, target, policy)
    else:
        with pytest.raises(ValueError):
            validate(task, target, policy)
