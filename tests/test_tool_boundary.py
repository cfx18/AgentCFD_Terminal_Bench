import json
from pathlib import Path
import time

import pytest

from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.harnesses.tools import ToolServer
from agentcfd_bench.records.transcript import Transcript
from agentcfd_bench.records.store import write_once


def test_script_cannot_be_final_solver(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    server = ToolServer(
        tmp_path / "native.sock",
        work,
        runner,
        Transcript(tmp_path),
        public_artifacts=tmp_path / "outputs",
    )
    with server:
        run = server.call({"operation": "exec", "argv": ["true"]})
        while runner.status(run["run_id"])["lifecycle"] == "running":
            time.sleep(0.05)
        with pytest.raises(ValueError, match="actual native run"):
            server.call({"operation": "submit", "run_id": run["run_id"]})
        with pytest.raises(ValueError):
            server.call({"operation": "grade", "run_id": run["run_id"]})


def test_all_installed_native_names_are_allowed(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    foam = tmp_path / "foam"
    (foam / "bin").mkdir(parents=True)
    for name in ("readFieldsTool", "newSolverNotKnownToHarness"):
        program = foam / "bin" / name
        program.write_text("#!/bin/sh\necho Native\n")
        program.chmod(0o755)
    runner = Runner(tmp_path / "native", Sandbox(foam_root=str(foam)), seconds=5)
    for name in ("readFieldsTool", "newSolverNotKnownToHarness"):
        run = runner.start(work, [name], kind="run")
        while runner.status(run["run_id"])["lifecycle"] == "running":
            time.sleep(0.05)
        assert runner.status(run["run_id"])["success"]


def test_logs_retain_valid_equation_paths_and_dimensions(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    text = "Incompatible dimensions: [1 -1 -3 0 0 0 0] -= [0 2 -3 0 0 0 0] at /work/system/controlDict"
    run = runner.start(work, ["/usr/bin/python3", "-c", f"print({text!r})"])
    while runner.status(run["run_id"])["lifecycle"] == "running":
        time.sleep(0.05)
    assert runner.logs(run["run_id"])["text"] == text + "\n"


def test_public_outputs_are_mounted_read_only(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    out = tmp_path / "public"
    out.mkdir()
    (out / "T").write_text("native")
    import subprocess

    command = Sandbox().command(
        work,
        ["/bin/sh", "-c", "echo fake > /artifacts/T"],
        readonly=[(out, "/artifacts")],
    )
    result = subprocess.run(command, capture_output=True)
    assert result.returncode != 0 and (out / "T").read_text() == "native"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"operation": "unknown"},
        {"operation": "status"},
        {"operation": "exec", "argv": "echo unsafe"},
        {"operation": "exec", "argv": ["true"], "seconds": float("nan")},
        {"operation": "logs", "run_id": "../../private"},
        {"operation": "logs", "run_id": "r-0123456789abcdef", "size": "bad"},
    ],
)
def test_invalid_rpc_is_structured_error_not_broken_pipe(tmp_path, payload):
    work = tmp_path / "work"
    work.mkdir()
    runner = Runner(tmp_path / "native", Sandbox(), seconds=5)
    server = ToolServer(
        tmp_path / "native.sock",
        work,
        runner,
        Transcript(tmp_path),
        public_artifacts=tmp_path / "outputs",
    )
    import httpx

    with (
        server,
        httpx.Client(
            transport=httpx.HTTPTransport(uds=str(tmp_path / "native.sock"))
        ) as client,
    ):
        # Deliberately permit NaN on the test wire to exercise hostile JSON input.
        response = client.post(
            "http://localhost/tools",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "ValueError"


def test_native_proxy_checks_embedded_tool_declarations():
    from agentcfd_bench.harnesses._transport.adapters.native_responses import (
        local_request_tools,
    )

    assert local_request_tools(
        {
            "input": [
                {
                    "type": "additional_tools",
                    "tools": [
                        {
                            "type": "namespace",
                            "name": "functions",
                            "tools": [{"type": "custom", "name": "exec"}],
                        }
                    ],
                }
            ]
        }
    )
    assert not local_request_tools(
        {"input": [{"type": "additional_tools", "tools": [{"type": "web_search"}]}]}
    )
