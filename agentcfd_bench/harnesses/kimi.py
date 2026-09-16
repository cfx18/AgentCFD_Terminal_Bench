"""Pinned Node Kimi Code, real session/tools, host-only Moonshot credentials.

No replacement agent loop. The shared namespace, native service, transcript and
request broker have the same ownership boundary as the Codex experiment.
"""

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from urllib.parse import urlsplit

from .codex import Codex, namespace
from .tools import ToolServer
from ..records.store import read, write_once, digest
from ..records.transcript import Transcript, capture_pipe

PACKAGE = "@moonshot-ai/kimi-code"
VERSION = "0.28.1"

# Actual installed 0.28.1 supports permission rules (not the later tools.disabled
# setting). Freeze them read-only; deny rules take precedence over auto approval.
CLIENT_CONFIG = """telemetry = false
default_permission_mode = "auto"
merge_all_available_skills = false

[loop_control]
max_steps_per_turn = 0
max_retries_per_step = 1

[model_catalog]
refresh_interval_ms = 0
refresh_on_start = false

[background]
keep_alive_on_exit = false
""" + "".join(
    '\n[[permission.rules]]\ndecision = "deny"\npattern = ' + json.dumps(name) + "\n"
    for name in ("Agent", "AgentSwarm", "WebSearch", "FetchURL", "CronCreate")
)


def validate_settings(settings):
    if settings.get("backend") != "custom-api":
        raise ValueError("Kimi Code requires an explicit custom-api backend")
    if settings.get("reasoning_effort") is not None:
        raise ValueError("This Kimi profile preserves the provider reasoning default")
    if (
        type(settings.get("context_window")) is not int
        or settings["context_window"] <= 0
    ):
        raise ValueError("Declare the provider's context window for native compaction")
    endpoint = urlsplit(settings["endpoint"])
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ValueError("Endpoint must not embed credentials or query parameters")
    if endpoint.scheme != "https" and endpoint.hostname not in (
        "127.0.0.1",
        "localhost",
    ):
        raise ValueError("A secure provider endpoint is required")
    if not settings.get("runtime") or not settings.get("api_key_env"):
        raise ValueError("Pinned runtime and credential variable are required")


def credentials(settings):
    """Never source shell code or fall back to another account/endpoint."""
    if settings.get("env_file"):
        from dotenv import dotenv_values

        values = dotenv_values(settings["env_file"], interpolate=False)
        key = values.get(settings["api_key_env"])
        endpoint_key = settings.get("endpoint_env")
        if endpoint_key and (values.get(endpoint_key) or "").rstrip("/") != settings[
            "endpoint"
        ].rstrip("/"):
            raise ValueError("Credential file endpoint differs from frozen experiment")
    else:
        key = os.environ.get(settings["api_key_env"])
    if not key:
        raise ValueError("Configured Kimi credential is missing (host only)")
    return key


def runtime_identity(runtime):
    root = Path(runtime).resolve(strict=True)
    package = read(root / PACKAGE / "package.json")
    if package.get("name") != PACKAGE or package.get("version") != VERSION:
        raise ValueError("Expected pinned Node Kimi Code 0.28.1, not Python kimi-cli")
    # Include dependencies and symlink targets, not just the launcher filename.
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            path.resolve(strict=True).relative_to(root)
        if path.is_file():
            with path.open("rb") as stream:
                files[path.relative_to(root).as_posix()] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
    return {
        "path": str(root),
        "package": PACKAGE,
        "version": VERSION,
        "content_identity": digest(files),
    }


class KimiCode(Codex):
    def run(self, prompt, remaining_calls, *, session=None):
        from ._transport.smoke.broker import Broker
        from ._transport.telemetry import collect

        settings = self.config["harness"]
        validate_settings(settings)
        credential = credentials(settings)
        self.transcript = Transcript(
            self.root, source="kimi-code", secrets=(credential,)
        )
        index = len(list((self.root / "calls").glob("turn-*"))) + 1
        turn = self.root / "calls" / f"turn-{index:04d}"
        turn.mkdir(parents=True)
        sockets = Path(tempfile.mkdtemp(prefix="of-v3-kimi-"))
        broker = Broker(
            turn / "api",
            sockets / "broker.sock",
            endpoint=settings["endpoint"],
            credential=credential,
            model=self.config["model"],
            limit=remaining_calls,
            seconds=self.config["budget"]["request_seconds"],
            transcript=self.transcript,
            guard_retries=True,
            native_chat=True,
        )
        (self.home / ".kimi-code").mkdir(exist_ok=True)
        (self.home / "empty-skills").mkdir(exist_ok=True)
        config_path = turn / "kimi-config.toml"
        with config_path.open("x") as output:
            output.write(CLIENT_CONFIG)
        environment = {
            "NO_COLOR": "1",
            "CI": "1",
            "IS_SANDBOX": "1",
            "KIMI_CODE_HOME": "/home/agent/.kimi-code",
            "KIMI_MODEL_NAME": self.config["model"],
            "KIMI_MODEL_API_KEY": "local-broker-placeholder",
            "KIMI_MODEL_BASE_URL": "http://127.0.0.1:8765/v1",
            "KIMI_MODEL_PROVIDER_TYPE": "openai",
            "KIMI_MODEL_MAX_CONTEXT_SIZE": str(settings["context_window"]),
            "KIMI_CODE_NO_AUTO_UPDATE": "true",
            "KIMI_DISABLE_TELEMETRY": "true",
        }
        command = [
            "/usr/bin/env",
            *(k + "=" + v for k, v in environment.items()),
            "/usr/bin/node",
            "--import",
            "/opt/kimi_fetch.mjs",
            "/opt/kimi/@moonshot-ai/kimi-code/dist/main.mjs",
            "--skills-dir",
            "/home/agent/empty-skills",
            "--output-format",
            "stream-json",
            "--prompt",
            prompt,
        ]
        if session:
            command += ["--session", session]
        argv = namespace(
            self.work,
            self.home,
            sockets,
            self.public,
            self.docs,
            self.artifacts,
            None,
            command,
            executable="/usr/bin/node",
            readonly=[
                (settings["runtime"], "/opt/kimi"),
                (Path(__file__).with_name("kimi_fetch.mjs"), "/opt/kimi_fetch.mjs"),
                (config_path, "/home/agent/.kimi-code/config.toml"),
            ],
        )
        tools = ToolServer(
            sockets / "native.sock",
            self.work,
            self.runner,
            self.transcript,
            public_artifacts=self.artifacts,
        )
        self.transcript.emit("prompt", {"text": prompt})
        write_once(
            turn / "launch.json",
            {
                "argv": argv,
                "model": self.config["model"],
                "backend": settings["backend"],
                "session": session,
                "harness": "kimi-code",
                "version": VERSION,
                "benchmark_output_token_cap": None,
            },
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
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                start_new_session=True,
                env={"PATH": "/usr/bin:/bin"},
            )
            write_once(turn / "process.json", {"pid": child.pid})
            self.transcript.emit("process_started", {"pid": child.pid})
            try:
                child.wait(
                    timeout=self.client_timeout(remaining_calls)
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
            self.transcript.emit(
                "process_exit", {"code": child.returncode, "calls": broker.calls}
            )
        events = []
        for line in (turn / "events.jsonl").read_text().splitlines():
            if line.strip():
                try:
                    events.append(json.loads(line))
                except ValueError:
                    events.append({"type": "unparsed_client_output", "text": line})
        for event in events:
            session = event.get("session_id") or session
        assistant = [e for e in events if e.get("role") == "assistant"]
        completed = bool(
            assistant
            and assistant[-1].get("content")
            and not assistant[-1].get("tool_calls")
            and session
            and not any(e.get("type") == "error" for e in events)
        )
        usage = collect(turn / "api")
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
            "completed": completed,
            "errors": broker.errors,
            "exit_code": child.returncode,
            "budget_exhausted": broker.budget_exhausted,
        }
        write_once(turn / "result.json", result)
        self.transcript.emit("client_result", result)
        return result
