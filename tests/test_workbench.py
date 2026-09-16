from pathlib import Path
import hashlib
import json
import subprocess
import time

import pytest

from agentcfd_bench.execution.files import inventory, snapshot
from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.records.store import read, write_once
from agentcfd_bench.tasks.loader import Task
from agentcfd_bench.grading.convergence import check

PROJECT = Path(__file__).resolve().parents[1]


def wait(runner, run):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        result = runner.status(run["run_id"])
        if result["lifecycle"] != "running":
            return result
        time.sleep(0.05)
    pytest.fail("Native test did not terminate")


def test_archive_unchanged():
    expected = read(PROJECT / "docs/archive-v2-inventory.json")
    for name, sha in expected.items():
        assert (
            hashlib.sha256(
                (PROJECT / "agentcfd_bench_old" / name).read_bytes()
            ).hexdigest()
            == sha
        )


def test_no_new_imports_from_archive():
    for path in (PROJECT / "agentcfd_bench").rglob("*.py"):
        assert "import agentcfd_bench_old" not in path.read_text()
        assert "from agentcfd_bench_old" not in path.read_text()


def test_namespace_is_real_and_offline():
    assert Sandbox().probe()["network"] == "no_network"


def test_snapshot_does_not_parse_openfoam(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "controlDict").write_text(
        'libs ("libfvOptions.so"); type readFields; expression "a/b"; type scalarTransport;'
    )
    (source / "binary").write_bytes(b"\0\xff\x01")
    assert snapshot(source, tmp_path / "copy") == inventory(source)


def test_snapshot_symlink_escape(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "secret").symlink_to("/etc/passwd")
    with pytest.raises(ValueError):
        snapshot(source, tmp_path / "copy")


def test_normal_native_and_immutable_result(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    run = runner.start(
        work,
        [
            "/bin/bash",
            "-c",
            'mkdir -p 0.1; echo temperature > 0.1/T; echo "a/b is not a path"',
        ],
    )
    result = wait(runner, run)
    assert result["success"] and result["exit_code"] == 0
    root, _ = runner.verify(run["run_id"])
    assert (root / "artifacts/0.1/T").read_text() == "temperature\n"
    assert "a/b is not a path" in runner.logs(run["run_id"])["text"]
    assert 0 < runner.remaining() < 5
    (root / "artifacts/0.1/T").write_text("tampered")
    with pytest.raises(RuntimeError, match="changed"):
        runner.verify(run["run_id"])


def test_failure_retains_fields_and_original_stderr(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    run = runner.start(
        work,
        [
            "/bin/bash",
            "-c",
            'mkdir -p 0.5; echo partial > 0.5/U; echo "FOAM FATAL: alpha missing at /work/constant/transportProperties" >&2; exit 2',
        ],
    )
    result = wait(runner, run)
    assert result["exit_code"] == 2 and not result["success"]
    root, _ = runner.verify(run["run_id"])
    assert (root / "artifacts/0.5/U").exists()
    assert (
        "/work/constant/transportProperties"
        in runner.logs(run["run_id"], stream="stderr")["text"]
    )


def test_timeout_retains_fields(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(tmp_path / "native", Sandbox(), seconds=3)
    run = runner.start(
        work, ["/bin/bash", "-c", "echo partial > U; sleep 5"], seconds=0.4
    )
    result = wait(runner, run)
    assert result["termination"] == "budget_exhausted"
    assert (runner.directory(run["run_id"]) / "artifacts/U").read_text() == "partial\n"


def test_live_log_and_cancel(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    run = runner.start(work, ["/bin/bash", "-c", "echo progressing; sleep 4"])
    deadline = time.monotonic() + 3
    while not runner.logs(run["run_id"])["text"] and time.monotonic() < deadline:
        time.sleep(0.05)
    assert "progressing" in runner.logs(run["run_id"])["text"]
    runner.cancel(run["run_id"])
    assert wait(runner, run)["termination"] == "cancelled"


def test_exit_before_collection_resume_without_execution(tmp_path):
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    root = runner.root / "r-0123456789abcdef"
    root.mkdir()
    (root / "case").mkdir()
    (root / "case/T").write_text("saved")
    (root / "stdout.log").write_text("End\n")
    (root / "stderr.log").write_text("")
    write_once(root / "spec.json", {"kind": "run", "seconds": 5})
    write_once(root / "dispatch.json", {"state": "dispatch_intent"})
    write_once(
        root / "exit.json",
        {"exit_code": 0, "termination": "exited", "elapsed_seconds": 1},
    )
    assert runner.status(root.name)["success"]
    assert runner.status(root.name) == runner.status(root.name)
    assert not (root / "worker.json").exists() and runner.remaining() == 4


def test_unknown_execution_is_not_reissued(tmp_path):
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    root = runner.root / "r-0123456789abcdef"
    root.mkdir()
    write_once(root / "spec.json", {"seconds": 5})
    write_once(root / "dispatch.json", {})
    assert runner.status(root.name)["lifecycle"] == "interrupted"
    assert runner.remaining() == 0
    with pytest.raises(RuntimeError):
        runner.start(tmp_path, ["true"])


@pytest.mark.parametrize("task_id", ["s-202", "s-203", "s-204", "s-205"])
def test_task_public_private_separation(tmp_path, task_id):
    task = Task.load(PROJECT / "tasks/releases/workbench-v3" / task_id)
    task.public_to(tmp_path / "public")
    assert not list((tmp_path / "public").rglob("reference.json"))
    assert not list((tmp_path / "public").rglob("grading.json"))
    assert "task_contract" not in task.public_prompt()
    assert task.private()[0]["task_id"] == task_id


def test_convergence_missing_is_not_success():
    rules = [{"name": "heat", "path": ["heat"], "max": 0.01}]
    assert check({}, rules)["heat"]["status"] == "not_evaluated"
    assert not check({}, rules)["heat"]["passed"]
    assert check({"heat": 0.005}, rules)["heat"]["passed"]
    assert not check({"heat": float("nan")}, rules)["heat"]["passed"]


def test_cli_rejects_implicit_paid_run():
    result = subprocess.run(
        [
            __import__("sys").executable,
            "-m",
            "agentcfd_bench",
            "run",
            "experiments/workbench-v3.yaml",
        ],
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2 and "--allow-paid" in result.stderr
