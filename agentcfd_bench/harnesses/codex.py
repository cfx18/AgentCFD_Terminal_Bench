"""Pinned Codex CLI + preserved subscription/custom-API relay, no new agent loop."""

import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile

from ..execution.sandbox import BWRAP, VENDOR
from ..records.store import write_once, read
from ..records.transcript import Transcript, capture_pipe
from .tools import ToolServer
from . import research

CODEX = VENDOR / "bin/codex"
PROTOCOL = """
Execution protocol:
Your case root is /work. Only this task's public inputs and frozen OpenFOAM v2306
documentation under /docs are available. Public internet, other tasks, reference
answers and graders are not accessible. Use local file/shell tools to build your case.
Use python3 /opt/foamctl.py exec -- <command> [args...] for native preparation,
meshing, checking or analysis. Scripts are allowed inside the native sandbox.
Use python3 /opt/foamctl.py run -- <native-executable> [args...] for a solver run.
OpenFOAM solver execution in this environment is serial-only. MPI parallel runs
are not supported: do not use mpirun, mpiexec, or the solver's -parallel option.
Run the solver directly through the run command above and plan for serial execution.
All installed native tools and libraries are available; no function-object allowlist.
Both commands return a run_id. Use status, logs, cancel with that ID. Poll existing
runs, do not reissue unknown operations. Completed or failed outputs are read-only
under /artifacts/<run_id>/. Copy needed preparation/mesh outputs back into /work
before the next operation. Each operation snapshots /work; preparations are not
silently injected into later runs. Failed runs retain saved fields and full logs.
Use short diagnostic runs if useful. If a finite native-time budget is configured,
all native commands share it. Solver completion alone does not establish physical accuracy.
Submit your chosen successful solver run using: python3 /opt/foamctl.py submit <run_id>.
Submission ends this task; GT comparison is private and is not available for tuning.
Natural-language replies are not submission actions. No report JSON is required.
Give concise public decision summaries, including search keywords, useful retrieved
evidence, what you changed and why. Do not reveal private chain-of-thought.
"""


def protocol_for(task, config=None):
    """Public-target reconstruction must not receive the hidden-target protocol."""
    meta = json.loads((task.root / "task.json").read_text())
    protocol = PROTOCOL
    if meta.get("track") == "dense-reconstruction":
        protocol = protocol.replace(
            "Public internet, other tasks, reference\nanswers and graders are not accessible.",
            "Public internet and other tasks are unavailable. The target observations\n"
            "under /input/observations/ are intentionally public for analysis and calibration.\n"
            "Original source cases, private provenance and grader implementation are not accessible.",
        ).replace(
            "Submission ends this task; GT comparison is private and is not available for tuning.",
            "Submission ends this task. You may compare your own outputs with the public\n"
            "observations; authoritative scoring independently reads the frozen native result.",
        )
    if config is not None and research.live(config):
        protocol = protocol.replace(
            "Only this task's public inputs and frozen OpenFOAM v2306\ndocumentation under /docs are available.",
            "This task's public inputs, frozen OpenFOAM v2306 documentation under /docs,\n"
            "and public web research through the native web tool are available.",
        ).replace(
            "Public internet, other tasks, reference\nanswers and graders are not accessible.",
            "Private reference answers, grader code and other task workspaces are not accessible.",
        ).replace(
            "Public internet and other tasks are unavailable.",
            "Other task workspaces are unavailable; public web research is enabled.",
        ).replace("Original source cases, private provenance and grader implementation are not accessible.",
                  "Private original source cases, provenance and grader implementation are not accessible.")
        protocol += research.PUBLIC_PROTOCOL
    return protocol


def namespace(work, home, sockets, public, docs, artifacts, catalog, command,
              *, executable=CODEX, readonly=()):
    transport = Path(__file__).parent / "_transport/adapters/codex_bridge.py"
    argv = [
        str(BWRAP),
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--cap-add",
        "CAP_NET_ADMIN",
        "--clearenv",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/lib64",
        "/lib64",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/home",
        "--dir",
        "/proc/self",
        "--symlink",
        str(executable),
        "/proc/self/exe",
        "--bind",
        str(work),
        "/work",
        "--bind",
        str(home),
        "/home/agent",
        "--dir",
        "/api",
        "--dir",
        "/opt",
        "--ro-bind",
        str(sockets / "broker.sock"),
        "/api/broker.sock",
        "--ro-bind",
        str(sockets / "native.sock"),
        "/api/native.sock",
        "--ro-bind",
        str(transport),
        "/opt/bridge.py",
        "--ro-bind",
        str(Path(__file__).with_name("foamctl.py")),
        "/opt/foamctl.py",
        "--ro-bind",
        str(public),
        "/input",
        "--ro-bind",
        str(docs),
        "/docs",
        "--ro-bind",
        str(artifacts),
        "/artifacts",
    ]
    if catalog:
        argv += ["--ro-bind", str(catalog), "/opt/model-catalog.json"]
    for source, destination in readonly:
        argv += ["--ro-bind", str(source), str(destination)]
    return argv + [
        "--chdir",
        "/work",
        "/usr/bin/python3",
        "/opt/bridge.py",
        "--",
        *command,
    ]


class Codex:
    def __init__(self, root, config, runner, public, docs):
        self.root = Path(root)
        self.config = config
        self.runner = runner
        self.public = Path(public)
        self.docs = Path(docs)
        self.work = self.root / "work"
        self.home = self.root / "cli-home"
        self.artifacts = self.root / "public-artifacts"
        for path in (self.work, self.home, self.artifacts):
            path.mkdir(parents=True, exist_ok=True)
        self.transcript = Transcript(self.root)

    @staticmethod
    def parse_events(path):
        events, malformed_events = [], []
        for number, line in enumerate(Path(path).read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                malformed_events.append({'line': number, 'message': str(exc), 'prefix': line[:200]})
        return events, malformed_events

    def run(self, prompt, remaining_calls, *, session=None):
        from ._transport.telemetry import collect

        web_live = research.live(self.config)

        index = len(list((self.root / "calls").glob("turn-*"))) + 1
        turn = self.root / "calls" / f"turn-{index:04d}"
        turn.mkdir(parents=True)
        sockets = Path(tempfile.mkdtemp(prefix="of-v3-"))
        settings = self.config["harness"]
        model = self.config["model"]
        backend = settings["backend"]
        catalog = None
        if backend == "chatgpt-subscription":
            from ._transport.adapters.native_responses import Broker
            from ._transport.adapters.subscription_auth import (
                SubscriptionAuth,
                ENDPOINT,
            )

            auth = SubscriptionAuth(settings.get("auth_home"))
            catalog = turn / "model-catalog.json"
            metadata = auth.catalog(model, settings["reasoning_effort"])
            write_once(turn / "provider-model-catalog.json", metadata)
            # Current CLI model metadata can enable v2 delegation despite feature=false.
            # This is an explicit harness capability setting, not a model substitution.
            metadata = json.loads(json.dumps(metadata))
            for entry in metadata["models"]:
                entry["multi_agent_version"] = None
                entry["multi_agent_reasoning_effort"] = None
            write_once(catalog, metadata)
            write_once(
                turn / "catalog-overrides.json",
                {
                    "purpose": "single_agent_experiment",
                    "multi_agent_version": None,
                    "multi_agent_reasoning_effort": None,
                },
            )
            broker = Broker(
                turn / "api",
                sockets / "broker.sock",
                endpoint=ENDPOINT,
                headers=auth.headers,
                model=model,
                limit=remaining_calls,
                seconds=self.config["budget"]["request_seconds"],
                network_proxy=auth.network_proxy,
                transcript=self.transcript,
                allow_web_search=web_live,
            )
        elif backend == "custom-api":
            from ._transport.smoke.broker import Broker

            credential = os.environ.get(settings["api_key_env"])
            if not credential:
                raise ValueError(
                    "Configured API credential environment variable is empty"
                )
            broker = Broker(
                turn / "api",
                sockets / "broker.sock",
                endpoint=settings["endpoint"],
                credential=credential,
                limit=remaining_calls,
                model=model,
                seconds=self.config["budget"]["request_seconds"],
                transcript=self.transcript,
                guard_retries=True,
            )
        else:
            raise ValueError("Unknown provider backend")
        options = [
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "--json",
            "-m",
            model,
        ]
        values = [
            'model_provider="benchmark"',
            'model_providers.benchmark.name="benchmark"',
            'model_providers.benchmark.base_url="http://127.0.0.1:8765/v1"',
            'model_providers.benchmark.wire_api="responses"',
            "model_providers.benchmark.request_max_retries=0",
            "model_providers.benchmark.stream_max_retries=0",
            "model_providers.benchmark.stream_idle_timeout_ms=720000",
            'web_search=' + json.dumps("live" if web_live else "disabled"),
            "model_providers.benchmark.supports_standalone_web_search=" + str(web_live).lower(),
            "features.multi_agent=false",
            "features.multi_agent_v2=false",
            "features.apps=false",
            "features.browser_use=false",
            "features.plugins=false",
        ]
        if catalog:
            values += [
                'model_catalog_json="/opt/model-catalog.json"',
                "model_reasoning_effort=" + json.dumps(settings["reasoning_effort"]),
                "model_providers.benchmark.requires_openai_auth=false",
            ]
        else:
            values += [
                "features.apply_patch_freeform=false",
                "model_supports_reasoning_summaries=false",
            ]
        for value in values:
            options += ["-c", value]
        command = (
            [str(CODEX), "exec"]
            + (["resume"] if session else [])
            + options
            + ([session] if session else [])
            + ["-"]
        )
        tools = ToolServer(
            sockets / "native.sock",
            self.work,
            self.runner,
            self.transcript,
            public_artifacts=self.artifacts,
        )
        argv = namespace(
            self.work,
            self.home,
            sockets,
            self.public,
            self.docs,
            self.artifacts,
            catalog,
            command,
        )
        self.transcript.emit("prompt", {"text": prompt})
        write_once(
            turn / "launch.json",
            {"argv": argv, "model": model, "backend": backend, "session": session,
             "research": research.facts(self.config)},
        )
        with (
            broker,
            tools,
            capture_pipe(turn / "events.jsonl", self.transcript) as out,
            capture_pipe(
                turn / "stderr.log", self.transcript, kind="client_stderr"
            ) as err,
        ):
            child = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                start_new_session=True,
                env={"PATH": "/usr/bin:/bin"},
            )
            write_once(turn / "process.json", {"pid": child.pid})
            try:
                child.communicate(
                    prompt.encode(),
                    timeout=self.client_timeout(remaining_calls),
                )
            except BaseException:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                write_once(
                    turn / "exit.json",
                    {
                        "code": child.returncode,
                        "interrupted": True,
                        "calls": broker.calls,
                    },
                )
                raise
            write_once(
                turn / "exit.json", {"code": child.returncode, "calls": broker.calls}
            )
        events, malformed_events = self.parse_events(turn / "events.jsonl")
        session = next(
            (e["thread_id"] for e in events if e.get("type") == "thread.started"),
            session,
        )
        usage = collect(turn / "api")
        # Reading /docs through shell is not measured by the legacy docs RPC counter.
        # Preserve actual tools/output in the transcript; do not invent "zero reads".
        usage["documentation"] = None
        result = {
            "calls": broker.calls,
            "session": session,
            "usage": usage,
            "documentation_evidence": {
                "mode": "local_files",
                "counts": "unknown",
                "source": "transcript.jsonl",
            },
            "completed": any(e.get("type") == "turn.completed" for e in events),
            "errors": broker.errors,
            "exit_code": child.returncode,
            "budget_exhausted": broker.budget_exhausted,
        }
        if malformed_events:
            result['malformed_events'] = malformed_events
        write_once(turn / "result.json", result)
        return result

    def client_timeout(self, remaining_calls):
        """No wall-clock task cap in unlimited mode; API watchdog stays separate."""
        remaining = self.runner.remaining()
        if remaining is None:
            return None
        return remaining_calls * (self.config["budget"]["request_seconds"] + 60) + remaining + 60
