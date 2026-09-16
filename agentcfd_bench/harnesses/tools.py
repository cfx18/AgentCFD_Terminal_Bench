"""Task-scoped Unix RPC. No API endpoint exposes GT, grading or host paths."""

from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import shutil
import socketserver
import threading

from ..execution.files import inventory
from ..records.store import write_once, read, lock


def reject_constant(value):
    raise ValueError("Non-finite JSON constants are not accepted")


class ToolServer:
    def __init__(self, socket, work, runner, transcript, *, public_artifacts):
        self.work, self.runner, self.transcript = Path(work), runner, transcript
        self.public_artifacts = Path(public_artifacts)
        self.public_artifacts.mkdir(parents=True, exist_ok=True)
        self.submission = runner.root.parent / "submission.json"
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                self.request.settimeout(60)
                super().setup()

            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if self.path != "/tools" or not 0 < length <= 65536:
                        raise ValueError("Invalid tool envelope")
                    request = json.loads(
                        self.rfile.read(length), parse_constant=reject_constant
                    )
                    owner.transcript.emit("native_request", request)
                    result = owner.call(request)
                    owner.transcript.emit("native_response", result)
                    code = 200
                except (ValueError, RuntimeError, OSError) as exc:
                    code = 400
                    result = {"error": type(exc).__name__, "message": str(exc)}
                    owner.transcript.emit("native_tool_error", result)
                data = json.dumps(result, ensure_ascii=False).encode()
                try:
                    self.send_response(code)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    owner.transcript.emit(
                        "native_delivery_error",
                        {"client_receipt": "unknown", "status": code},
                    )

        self.server = socketserver.UnixStreamServer(str(socket), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def call(self, request):
        if not isinstance(request, dict) or not isinstance(
            request.get("operation"), str
        ):
            raise ValueError("An operation name is required")
        operation = request["operation"]
        if operation not in ("exec", "run", "logs", "status", "cancel", "submit"):
            raise ValueError("Unknown operation")
        if operation in ("exec", "run"):
            if self.submission.exists():
                raise ValueError("Task is already submitted")
            argv = request.get("argv")
            if (
                not isinstance(argv, list)
                or not argv
                or not all(isinstance(v, str) and v and "\0" not in v for v in argv)
            ):
                raise ValueError("A nonempty string argument list is required")
            seconds = request.get("seconds")
            if seconds is not None and (
                type(seconds) not in (int, float) or not 0 < seconds < 1e9
            ):
                raise ValueError("A finite positive runtime is required")
            return self.runner.start(self.work, argv, kind=operation, seconds=seconds)
        run_id = request.get("run_id")
        if not isinstance(run_id, str):
            raise ValueError("A run identifier is required")
        if operation == "logs":
            return self.runner.logs(
                run_id,
                stream=request.get("stream", "stdout"),
                offset=request.get("offset", 0),
                size=request.get("size", 16000),
            )
        if operation == "cancel":
            return self.runner.cancel(run_id)
        if operation == "status":
            result = self.runner.status(run_id)
            if result["lifecycle"] == "completed":
                self.publish(run_id)
            return {
                **{k: v for k, v in result.items() if k != "artifacts"},
                "remaining_seconds": self.runner.remaining(),
                "artifact_directory": (
                    "/artifacts/" + run_id
                    if result["lifecycle"] == "completed"
                    else None
                ),
            }
        if operation == "submit":
            root, result = self.runner.verify(run_id)
            if result["kind"] != "run":
                raise ValueError(
                    "Submit an actual native run, not an arbitrary shell execution"
                )
            if not result["success"]:
                raise ValueError(
                    "The selected run did not complete successfully; inspect its logs"
                )
            with lock(self.runner.root / "submit.lock"):
                if self.submission.exists():
                    if read(self.submission)["run_id"] != run_id:
                        raise ValueError("A different run was already submitted")
                else:
                    write_once(self.submission, {"run_id": run_id})
            return {
                "submitted": True,
                "run_id": run_id,
                "message": "Submission recorded. Hidden GT scoring is not an interactive tool.",
            }
        raise ValueError("Unknown operation")

    def publish(self, run_id):
        root, result = self.runner.verify(run_id)
        destination = self.public_artifacts / run_id
        if not destination.exists():
            shutil.copytree(root / "artifacts", destination)
            for stream in ("stdout", "stderr"):
                shutil.copyfile(
                    root / (stream + ".log"), destination / (stream + ".log")
                )
        return destination

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
