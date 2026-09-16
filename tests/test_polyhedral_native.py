"""Bounded v2306 integration for the new production observation path."""

import json
from pathlib import Path
import re
import shutil
import time

import pytest

from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.grading.service import (
    grade_submission,
    export_native,
    artifact_text,
)
from agentcfd_bench.grading.evaluate import evaluate
from agentcfd_bench.grading.qualify_geometry import source_evidence
from agentcfd_bench.records.store import read
from agentcfd_bench.tasks.loader import Task

PROJECT = Path(__file__).resolve().parents[1]
AUDIT = PROJECT / "audits/polyhedral-qualification-20260916-003"
FOAM = PROJECT / "environments/native-v2306/foam"


def wait(runner, op):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        status = runner.status(op["run_id"])
        if status["lifecycle"] != "running":
            assert status["success"], runner.logs(op["run_id"], stream="stderr")
            return runner.verify(op["run_id"])[0]
        time.sleep(0.05)
    pytest.fail("Bounded native fixture timed out")


@pytest.mark.parametrize("write_format", ["ascii", "binary"])
def test_real_alternative_cross_section_mesh_and_private_grading(
    tmp_path, write_format
):
    target, inputs, _ = source_evidence("s-205")
    inputs["system/blockMeshDict"] = inputs["system/blockMeshDict"].replace(
        "(400 1 1)", "(200 2 2)"
    )
    for name, text in inputs.items():
        # The original patch groups four non-coplanar side faces: use the
        # per-face symmetry condition, not the planar-only symmetryPlane type.
        inputs[name] = re.sub(r"type\s+empty\s*;", "type symmetry;", text)
    inputs["system/controlDict"] = re.sub(
        r"writeFormat\s+ascii\s*;",
        f"writeFormat {write_format};",
        inputs["system/controlDict"],
    )
    work = tmp_path / "work"
    work.mkdir()
    for name, text in inputs.items():
        p = work / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    runner = Runner(
        tmp_path / "native", Sandbox(foam_root=str(FOAM), mpi="intelmpi"), seconds=60
    )
    for argv, kind in [
        (["blockMesh"], "exec"),
        (["setFields"], "exec"),
        (["rhoCentralFoam"], "run"),
    ]:
        op = runner.start(work, argv, kind=kind)
        native = wait(runner, op)
        shutil.copytree(native / "artifacts", work, dirs_exist_ok=True)
    task_root = tmp_path / "task"
    shutil.copytree(PROJECT / "tasks/releases/workbench-v3/s-205", task_root)
    shutil.copyfile(
        AUDIT / "s-205/reference.json", task_root / "private/reference.json"
    )
    task = Task.load(task_root)
    result = grade_submission(task, runner, op["run_id"], tmp_path / "grading")
    assert result["verdict"] == "pass", result
    assert result["measurements"]["cell_count"]["value"] == 800
    assert result["convergence_certified"] is False
    operations = list((tmp_path / "grading/export-runs").glob("r-*"))
    # Simulate the already-exported result not yet committed. Existing exit
    # receipts are replayed, never run again. Only this test's temp receipt goes.
    (tmp_path / "grading/result.json").unlink()
    recovered = grade_submission(task, runner, op["run_id"], tmp_path / "grading")
    assert recovered == result
    assert list((tmp_path / "grading/export-runs").glob("r-*")) == operations


@pytest.mark.parametrize("task_id", ["s-202", "s-203", "s-204", "s-205"])
def test_real_reference_replay_and_broken_evidence(task_id):
    target = read(AUDIT / task_id / "reference.json")
    artifacts = read(AUDIT / task_id / "artifacts.json")
    score = evaluate(task_id, artifacts, target, native_success=True)
    assert score["verdict"] == "pass", score
    assert not score["convergence_certified"]
    # Native success without actual field evidence must not score.
    bad = {
        k: v
        for k, v in artifacts.items()
        if not re.fullmatch(r"[0-9.eE+\-]+/(?:[^/]+/)?T", k)
    }
    broken = evaluate(task_id, bad, target, native_success=True)
    assert broken["verdict"] == "fail"


def test_native_multiregion_export_after_region_and_patch_rename(tmp_path):
    source = AUDIT / "s-202/work"
    work = tmp_path / "work"
    # Literal identifier rename, including mapped-region and boundary references.
    names = {
        "bottomWater": "liquid_custom",
        "topAir": "gas_custom",
        "heater": "source_custom",
        "leftSolid": "plate_alpha",
        "rightSolid": "plate_beta",
        "minX": "port_one",
        "maxX": "port_two",
    }

    def rename(text):
        for old, new in names.items():
            text = text.replace(old, new)
        return text

    for path in source.rglob("*"):
        if path.is_file():
            dest = work / rename(path.relative_to(source).as_posix())
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rename(path.read_text()))
    original = read(AUDIT / "s-202/artifacts.json")
    a, _ = export_native(
        work,
        "s-202",
        "chtMultiRegionFoam",
        tmp_path / "exports",
        Sandbox(foam_root=str(FOAM), mpi="intelmpi"),
        original["solver.log"],
        geometry_v2=True,
    )
    target = read(AUDIT / "s-202/reference.json")
    score = evaluate("s-202", a, target, native_success=True)
    assert score["verdict"] == "pass", score
    assert not (work / "constant/polyMesh").exists()
    assert "mesh/liquid_custom/points" in a


def test_latest_mesh_points_override_constant(tmp_path):
    for name, text in [
        ("constant/polyMesh/points", "old"),
        ("1/polyMesh/points", "middle"),
        ("10/polyMesh/points", "new"),
        ("constant/polyMesh/owner", "owner"),
    ]:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    a = artifact_text(tmp_path, "log")
    assert a["mesh/points"] == "new" and a["mesh/owner"] == "owner"
