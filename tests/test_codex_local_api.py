"""Actual installed CLI and namespaces; BOTH upstreams are local fake servers."""

import json
import shlex
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.harnesses.codex import Codex
from agentcfd_bench.harnesses._transport.adapters.codex_broker import (
    completed_response_events,
)


def test_malformed_codex_event_line_is_recorded_not_fatal(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"type":"thread.started","thread_id":"ok"}\n{"type":"partial"\n{"type":"turn.completed"}\n')
    parsed, malformed = Codex.parse_events(events)
    assert [item["type"] for item in parsed] == ["thread.started", "turn.completed"]
    assert malformed and malformed[0]["line"] == 2


@pytest.mark.parametrize("backend", ["custom-api", "chatgpt-subscription"])
@pytest.mark.parametrize("native_seconds", [10, None])
@pytest.mark.parametrize("exhaust", [False, True])
def test_actual_cli_tools_and_same_session_resume(tmp_path, monkeypatch, backend, native_seconds, exhaust,
                                                research_mode="disabled"):
    received = []
    searches = []
    program = """from pathlib import Path
import json, subprocess, socket
assert not Path('/root').exists()
assert not Path('/solution').exists()
assert not Path('/tests').exists()
assert socket.if_nameindex()==[(1,'lo')]
assert Path('/docs/example.md').read_text()=='offline documentation'
Path('case.txt').write_text('from real CLI')
p=subprocess.run(['python3','/opt/foamctl.py','exec','--','/bin/sh','-c','echo native-tool-ok'],capture_output=True,text=True)
assert p.returncode==0,p.stderr+p.stdout
assert json.loads(p.stdout)['lifecycle']=='running'
print('OFFLINE_TOOL_BOUNDARY_OK')
"""
    command = shlex.join(["python3", "-c", program])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path.endswith('/alpha/search'):
                searches.append(body)
                data = json.dumps({'output':'LOCAL_WEB_EVIDENCE: closed-volume pressure depends on mass.',
                    'results':[{'type':'text_result','ref_id':'turn0search0',
                                'url':'https://doc.openfoam.com/2306/'}]}).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            received.append(body)
            n = len(received)
            if backend == "custom-api":
                message = {"role": "assistant", "content": "Done."}
                if n == 1:
                    message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "exec_command",
                                    "arguments": json.dumps({"cmd": command}),
                                },
                            }
                        ],
                    }
                data = json.dumps(
                    {
                        "id": f"chat-{n}",
                        "object": "chat.completion",
                        "model": body["model"],
                        "choices": [
                            {
                                "index": 0,
                                "message": message,
                                "finish_reason": "tool_calls" if n == 1 else "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 20,
                            "total_tokens": 30,
                        },
                    }
                ).encode()
                mime = "application/json"
            else:
                output = [
                    {
                        "type": "message",
                        "role": "assistant",
                        "id": f"msg-{n}",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": "Done."}],
                    }
                ]
                if n == 1:
                    output = [
                        {
                            "type": "custom_tool_call",
                            "id": "fc_1",
                            "call_id": "call_1",
                            "name": "exec",
                            "namespace": "functions",
                            "input": ("text(await tools.web__run({search_query:[{q:'OpenFOAM closed cavity mass pressure'}]}));"
                                      if research_mode == 'web-search-live' else '')
                            + "text(await tools.exec_command("
                            + json.dumps({"cmd": command})
                            + "));",
                            "status": "completed",
                        }
                    ]
                response = {
                    "object": "response",
                    "id": f"resp-{n}",
                    "status": "completed",
                    "model": body["model"],
                    "output": output,
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 20,
                        "total_tokens": 30,
                    },
                }
                # Fake upstream emits genuine custom-tool SSE without the Chat adapter.
                events = [
                    {
                        "type": "response.created",
                        "response": {**response, "status": "in_progress", "output": []},
                    }
                ]
                for index, item in enumerate(output):
                    events.extend(
                        [
                            {
                                "type": "response.output_item.added",
                                "output_index": index,
                                "item": item,
                            },
                            {
                                "type": "response.output_item.done",
                                "output_index": index,
                                "item": item,
                            },
                        ]
                    )
                events.append({"type": "response.completed", "response": response})
                data = "".join(
                    "data: " + json.dumps(event) + "\n\n" for event in events
                ).encode()
                mime = "text/event-stream"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    if backend == "chatgpt-subscription":
        from agentcfd_bench.harnesses._transport.adapters import subscription_auth

        # Reads PUBLIC model metadata only. Never opens real auth.json.
        catalog = subscription_auth.SubscriptionAuth("/root/.codex").catalog(
            "gpt-6-astra", "xhigh"
        )

        class FakeAuth:
            network_proxy = None

            def __init__(self, *args):
                pass

            def headers(self):
                return {"Authorization": "Bearer LOCAL-FAKE-ONLY"}

            def catalog(self, *args):
                return catalog

        monkeypatch.setattr(subscription_auth, "SubscriptionAuth", FakeAuth)
        monkeypatch.setattr(subscription_auth, "ENDPOINT", endpoint + "/responses")
    monkeypatch.setenv("BENCH_LOCAL_TEST_KEY", "LOCAL-FAKE-ONLY")
    config = {
        "model": "gpt-6-astra" if backend == "chatgpt-subscription" else "Kimi-K3",
        "harness": {
            "backend": backend,
            "reasoning_effort": "xhigh",
            "endpoint": endpoint,
            "api_key_env": "BENCH_LOCAL_TEST_KEY",
        },
        "budget": {"request_seconds": 10},
        "network": research_mode,
    }
    public = tmp_path / "public"
    public.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "example.md").write_text("offline documentation")
    runner = Runner(tmp_path / "trial/native", Sandbox(), seconds=native_seconds)
    agent = Codex(tmp_path / "trial", config, runner, public, docs)
    try:
        first = agent.run(
            "Read local documentation, then exercise the native tools.", 1 if exhaust else 3
        )
        if exhaust:
            assert first['calls'] == len(received) == 1
            assert first['budget_exhausted'], first
            assert not first['completed'], first
            return
        assert first["completed"] and not first["errors"] and first["calls"] == 2, first
        assert first["usage"]["documentation"] is None
        assert (agent.work / "case.txt").read_text() == "from real CLI"
        again = agent.run("Continue the same task.", 1, session=first["session"])
        assert (
            again["completed"]
            and again["session"] == first["session"]
            and again["calls"] == 1
        ), again
        assert len(received) == 3
        # Responses Lite exposes web.run inside the code-mode declaration, not a
        # hosted top-level web_search. Verify the actual callable and transport.
        assert ('tools.web__run' in json.dumps(received)) == (research_mode == 'web-search-live')
        if research_mode == 'web-search-live':
            assert len(searches) == 1
            assert searches[0]['settings']['external_web_access'] is True
            assert searches[0]['commands']['search_query'][0]['q'] == 'OpenFOAM closed cavity mass pressure'
            assert 'LOCAL_WEB_EVIDENCE' in json.dumps(received[1])
            records = [json.loads(line) for line in (agent.root / 'transcript.jsonl').read_text().splitlines()]
            queries = [r for r in records if r['kind'] == 'web_retrieval']
            assert len(queries) == 1
            assert 'LOCAL_WEB_EVIDENCE' in queries[0]['payload']['response_text']
        else:
            assert not searches
        assert all(
            "max_output_tokens" not in r and "max_tokens" not in r for r in received
        )
        assert '"name": "spawn_agent"' not in json.dumps(received)
        events = "\n".join(
            p.read_text() for p in (tmp_path / "trial/calls").rglob("events.jsonl")
        )
        assert "OFFLINE_TOOL_BOUNDARY_OK" in events
        assert "reference.json" not in json.dumps(received)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_real_cli_live_search_wire_and_isolated_shell(tmp_path, monkeypatch):
    test_actual_cli_tools_and_same_session_resume(
        tmp_path, monkeypatch, 'chatgpt-subscription', None, False,
        research_mode='web-search-live',
    )
