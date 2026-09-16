"""Real pinned Node CLI + fake HTTP: no credentials or paid requests."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shlex
import threading
import time

import pytest

from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.harnesses.kimi import KimiCode, credentials, runtime_identity
from agentcfd_bench.harnesses._transport.journal import read_receipt
from agentcfd_bench.records.store import read

PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / ".harness-runtime/kimi-code-0.28.1/node_modules"


@contextmanager
def fake_agent(tmp_path, monkeypatch, respond, *, limit_seconds=10, sandbox=None, native_seconds=30):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(body)
            payload, status = respond(body, len(received))
            if payload is None:
                self.close_connection = True
                return
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("KIMI_LOCAL_TEST_KEY", "HOST-ONLY-LOCAL-TEST-SECRET")
    config = {
        "harness": {
            "name": "kimi-code",
            "backend": "custom-api",
            "runtime": str(RUNTIME),
            "context_window": 1048576,
            "endpoint": f"http://127.0.0.1:{server.server_port}/v1",
            "api_key_env": "KIMI_LOCAL_TEST_KEY",
        },
        "model": "kimi-k3",
        "budget": {"request_seconds": limit_seconds},
    }
    public, docs = tmp_path / "public", tmp_path / "docs"
    public.mkdir()
    docs.mkdir()
    (docs / "example.md").write_text("offline documentation")
    runner = Runner(tmp_path / "trial/native", sandbox or Sandbox(), seconds=native_seconds)
    agent = KimiCode(tmp_path / "trial", config, runner, public, docs)
    try:
        yield agent, received
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def response(body, n, command=None, *, finish=None):
    message = {"role": "assistant", "content": "Done."}
    if command:
        message = {
            "role": "assistant",
            "content": None,
            "reasoning_content": "Synthetic test reasoning, not a real model.",
            "tool_calls": [
                {
                    "id": f"call_{n}",
                    "type": "function",
                    "function": {
                        "name": "Bash",
                        "arguments": json.dumps({"command": command, "timeout": 15}),
                    },
                }
            ],
        }
    return {
        "id": f"fake-{n}",
        "object": "chat.completion",
        "model": body["model"],
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish or ("tool_calls" if command else "stop"),
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@pytest.mark.parametrize('native_seconds', [30, None])
def test_real_kimi_tools_logs_isolation_and_same_session(tmp_path, monkeypatch, native_seconds):
    program = """from pathlib import Path
import json, subprocess, socket, time, os
assert not Path('/root').exists()
assert not Path('/tests').exists()
assert not Path('/solution').exists()
assert socket.if_nameindex()==[(1,'lo')]
assert 'HOST-ONLY-LOCAL-TEST-SECRET' not in str(dict(os.environ))
assert Path('/docs/example.md').read_text()=='offline documentation'
try:
    Path('/home/agent/.kimi-code/config.toml').write_text('tamper')
except OSError:
    pass
else:
    raise AssertionError('Frozen capability config is writable')
Path('case.txt').write_text('from real Kimi Code')
def call(*args):
    p=subprocess.run(['python3','/opt/foamctl.py',*args],capture_output=True,text=True)
    assert p.returncode==0,p.stderr+p.stdout
    return json.loads(p.stdout)
run=call('exec','--','/bin/sh','-c','echo NATIVE_TEST_ERROR >&2; exit 2')
for _ in range(100):
    status=call('status',run['run_id'])
    if status['lifecycle']!='running':break
    time.sleep(.05)
assert status['exit_code']==2,status
logs=call('logs',run['run_id'],'--stream','stderr')
assert 'NATIVE_TEST_ERROR' in logs['text'],logs
print('KIMI_OFFLINE_BOUNDARY_OK',logs['text'])
"""
    command = shlex.join(["python3", "-c", program])
    with fake_agent(
        tmp_path,
        monkeypatch,
        lambda b, n: (response(b, n, command if n == 1 else None), 200),
        native_seconds=native_seconds,
    ) as (agent, received):
        first = agent.run("Use your shell to inspect docs and native failure logs.", 3)
        assert first["completed"] and first["calls"] == 2 and not first["errors"], first
        assert first["session"]
        assert (agent.work / "case.txt").read_text() == "from real Kimi Code"
        second = agent.run("Continue the same task.", 1, session=first["session"])
        assert second["session"] == first["session"] and second["completed"], second
        assert len(received) == 3
        assert all(b["model"] == "kimi-k3" for b in received)
        # Kimi Code itself requests 131072 tokens; the benchmark neither adds nor
        # reduces that native setting. Verify complete client-to-wire equality.
        calls = sorted((agent.root / "calls").glob("turn-*/api/call-*/request.json"))
        for path, wire in zip(calls, received, strict=True):
            client = read_receipt(path)["body"]
            expected = {**client, "stream": False}
            expected.pop("stream_options", None)
            assert wire == expected
        assert "KIMI_OFFLINE_BOUNDARY_OK" in json.dumps(received[1]["messages"])
        assert "Synthetic test reasoning" in json.dumps(received[1]["messages"])
        assert "from real Kimi Code" in json.dumps(received[2]["messages"])
        assert (
            "HOST-ONLY-LOCAL-TEST-SECRET"
            not in (agent.root / "transcript.md").read_text()
        )


@pytest.mark.parametrize("mode", ["malformed", "upstream_error", "budget"])
def test_terminal_errors_no_paid_retry_and_total_budget(tmp_path, monkeypatch, mode):
    def respond(body, n):
        if mode == "upstream_error":
            return {"error": {"message": "fake upstream unavailable"}}, 503
        value = response(body, n, "echo local-tool" if mode == "budget" else None)
        if mode == "malformed":
            value["choices"][0]["message"] = {"role": "assistant", "content": None}
        return value, 200

    with fake_agent(tmp_path, monkeypatch, respond) as (agent, received):
        result = agent.run("Local interface check.", 1)
        assert len(received) == result["calls"] == 1
        assert not result["completed"]
        assert result["budget_exhausted"] if mode == "budget" else result["errors"]
        assert read(agent.root / "calls/turn-0001/exit.json")["calls"] == 1


def test_explicit_identity_and_no_endpoint_fallback(tmp_path):
    value = runtime_identity(RUNTIME)
    assert value["package"] == "@moonshot-ai/kimi-code" and value["version"] == "0.28.1"
    env = tmp_path / "fake.env"
    env.write_text("KEY=fake\nBASE=https://wrong.invalid/v1\n")
    with pytest.raises(ValueError, match="endpoint differs"):
        credentials(
            {
                "env_file": str(env),
                "api_key_env": "KEY",
                "endpoint_env": "BASE",
                "endpoint": "https://api.moonshot.cn/v1",
            }
        )


def test_unknown_response_is_saved_and_never_automatically_replayed(
    tmp_path, monkeypatch
):
    with fake_agent(tmp_path, monkeypatch, lambda b, n: (None, 200)) as (
        agent,
        received,
    ):
        result = agent.run("Local disconnect test.", 3)
        assert result["calls"] == len(received) == 1
        assert result["errors"] and not result["errors"][0]["known_response"]
        assert not result["completed"]
        assert (agent.root / "calls/turn-0001/result.json").is_file()


def test_cli_cannot_delegate_or_search_web(tmp_path, monkeypatch):
    def respond(body, n):
        value = response(body, n)
        if n == 1:
            value["choices"][0].update(
                finish_reason="tool_calls",
                message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "agent-denied",
                            "type": "function",
                            "function": {
                                "name": "Agent",
                                "arguments": json.dumps(
                                    {
                                        "description": "Forbidden child test",
                                        "prompt": "Reply with CHILD-SHOULD-NOT-RUN",
                                        "subagent_type": "coder",
                                    }
                                ),
                            },
                        },
                        {
                            "id": "web-denied",
                            "type": "function",
                            "function": {
                                "name": "WebSearch",
                                "arguments": json.dumps(
                                    {"query": "FORBIDDEN_NETWORK_TEST"}
                                ),
                            },
                        },
                    ],
                },
            )
        return value, 200

    with fake_agent(tmp_path, monkeypatch, respond) as (agent, received):
        result = agent.run("Test denied capabilities.", 3)
        assert result["completed"] and not result["errors"], result
        assert len(received) == 2
        observed = [m for m in received[-1]["messages"] if m["role"] == "tool"]
        assert len(observed) == 2
        outcomes = {m["tool_call_id"]: m["content"] for m in observed}
        assert '"Agent" was denied by permission rule' in outcomes["agent-denied"]
        # No web service is configured: the real CLI does not even register it.
        assert '"WebSearch" not found' in outcomes["web-denied"]


def test_actual_kimi_explicit_native_submission(tmp_path, monkeypatch):
    # Tiny real OpenFOAM run selected by a LOCAL FAKE provider. Only test inputs
    # are staged in /work; no GT/acceptance files are mounted or sent to an API.
    from agentcfd_bench.tasks.loader import Task

    task = Task.load(PROJECT / "tasks/releases/workbench-v3/s-205")
    target, _ = task.private()
    inputs = read_receipt(Path(target["source"]["run_directory"]) / "inputs.json")
    program = """import json, subprocess, time, shutil
def call(*args):
    p=subprocess.run(['python3','/opt/foamctl.py',*args],capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    return json.loads(p.stdout)
for kind,name in [('exec','blockMesh'),('exec','setFields'),('run','rhoCentralFoam')]:
    run=call(kind,'--',name)
    for _ in range(400):
        status=call('status',run['run_id'])
        if status['lifecycle']!='running':break
        time.sleep(.05)
    assert status['success'],status
    if kind=='exec':
        shutil.copytree(status['artifact_directory'],'/work',dirs_exist_ok=True)
submitted=call('submit',run['run_id'])
assert submitted['submitted'],submitted
print('NATIVE_SUBMISSION_OK')
"""
    command = shlex.join(["python3", "-c", program])
    sandbox = Sandbox(
        foam_root=str(PROJECT / "environments/native-v2306/foam"), mpi="intelmpi"
    )
    with fake_agent(
        tmp_path,
        monkeypatch,
        lambda b, n: (response(b, n, command if n == 1 else None), 200),
        sandbox=sandbox,
    ) as (agent, received):
        for name, content in inputs.items():
            path = agent.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        result = agent.run(
            "Execute the local native test fixture, then explicitly submit.", 3
        )
        assert result["completed"] and not result["errors"], result
        assert "NATIVE_SUBMISSION_OK" in json.dumps(received[-1]["messages"])
        selected = read(agent.root / "submission.json")["run_id"]
        _, receipt = agent.runner.verify(selected)
        assert receipt["success"] and receipt["kind"] == "run"
