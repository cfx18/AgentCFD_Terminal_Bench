"""Bounded local OpenFOAM integration, never calls a model or cluster scheduler."""

import json
from pathlib import Path
import shutil
import time

import pytest

from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.grading.service import grade_submission
from agentcfd_bench.tasks.loader import Task

PROJECT = Path(__file__).resolve().parents[1]
FOAM = PROJECT / "environments/native-v2306/foam"


def wait(runner, operation):
    until = time.monotonic() + 90
    while time.monotonic() < until:
        result = runner.status(operation["run_id"])
        if result["lifecycle"] != "running":
            return result
        time.sleep(0.05)
    pytest.fail("Local native integration did not finish")


@pytest.mark.parametrize(
    "tool",
    [
        "foamDictionary",
        "blockMesh",
        "checkMesh",
        "snappyHexMesh",
        "topoSet",
        "setFields",
        "pimpleFoam",
        "rhoCentralFoam",
        "foamFormatConvert",
        "postProcess",
    ],
)
def test_installed_tool_dependencies(tmp_path, tool):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(
        tmp_path / "native", Sandbox(foam_root=str(FOAM), mpi="intelmpi"), seconds=10
    )
    run = runner.start(work, [tool, "-help"], kind="run")
    assert wait(runner, run)["success"], runner.logs(run["run_id"], stream="stderr")


def test_native_dictionary_errors_not_python_allowlist(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    path = work / "dictionary"
    path.write_text(
        "FoamFile {version 2.0; format ascii; class dictionary; object dictionary;}\n"
        'libs ("libfvOptions.so"); functions { reader {type readFields; fields (U T); } '
        'transport {type scalarTransport; expression "a/b";} }\n'
    )
    runner = Runner(
        tmp_path / "native", Sandbox(foam_root=str(FOAM), mpi="intelmpi"), seconds=10
    )
    good = runner.start(work, ["foamDictionary", "dictionary"])
    assert wait(runner, good)["success"]
    path.write_text("FoamFile { version 2.0;\nformat ascii; class dictionary;")
    bad = runner.start(work, ["foamDictionary", "dictionary"])
    assert not wait(runner, bad)["success"]
    assert "FOAM FATAL" in runner.logs(bad["run_id"], stream="stderr")["text"]


@pytest.mark.parametrize("write_format", ["ascii", "binary"])
def test_real_shock_native_to_private_grader(tmp_path, write_format):
    task = Task.load(PROJECT / "tasks/releases/workbench-v3/s-205")
    target, _ = task.private()
    source = Path(target["source"]["run_directory"])
    inputs = json.loads((source / "inputs.json").read_text())["payload"]
    import re

    inputs["system/controlDict"] = re.sub(
        r"writeFormat\s+ascii\s*;",
        f"writeFormat {write_format};",
        inputs["system/controlDict"],
    )
    work = tmp_path / "work"
    work.mkdir()
    # Existing reviewed tiny 400-cell fixture; no hidden data are exposed to a model.
    for name, text in inputs.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    runner = Runner(
        tmp_path / "native", Sandbox(foam_root=str(FOAM), mpi="intelmpi"), seconds=60
    )
    for argv, kind in [
        (["blockMesh"], "exec"),
        (["setFields"], "exec"),
        (["rhoCentralFoam"], "run"),
    ]:
        operation = runner.start(work, argv, kind=kind)
        result = wait(runner, operation)
        assert result["success"], runner.logs(operation["run_id"], stream="stderr")
        native, _ = runner.verify(operation["run_id"])
        shutil.copytree(native / "artifacts", work, dirs_exist_ok=True)
    outcome = grade_submission(task, runner, operation["run_id"], tmp_path / "grading")
    assert outcome["verdict"] == "pass", outcome
    assert outcome["checks"]["reference_match"]
    assert outcome["convergence_certified"] is False
    assert (
        grade_submission(task, runner, operation["run_id"], tmp_path / "grading")
        == outcome
    )
