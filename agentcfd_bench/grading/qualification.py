"""Readiness is bound to tested grading code and a specific reference version."""

from pathlib import Path
from ..execution.files import inventory
from ..records.store import digest, read
from .observations import VERSION


def grader_identity():
    files = inventory(Path(__file__).parent)
    selected = {
        name: value
        for name, value in files.items()
        if name.endswith(".py")
        and (
            name.startswith(("physics/", "dense"))
            or name
            in (
                "geometry.py",
                "observations.py",
                "service.py",
                "evaluate.py",
                "convergence.py",
            )
        )
    }
    return digest(selected)


def validate(task, target, policy):
    if policy.get('policy') == 'dense-observation-v1' and policy.get('release_status') == 'released':
        from .dense_qualification import validate as validate_dense
        return validate_dense(task, target, policy)
    if target.get("observation_version") != VERSION:
        return
    proof = read(task.root / "private/qualification.json")
    if (
        proof.get("grader_identity") != grader_identity()
        or proof.get("reference_identity") != digest(target)
        or proof.get("task_id") != task.task_id
        or proof.get("reference_replay") != "pass"
        or proof.get("corrupt_field_rejected") is not True
        or proof.get("regression_tests_passed") is not True
        or policy.get("observation_version") != VERSION
    ):
        raise ValueError("Grader qualification evidence missing, stale or mismatched")
