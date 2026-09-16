"""Independent host worker. Persists exit first, then collects even failed fields."""

import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import uuid

from .files import inventory, snapshot
from .sandbox import Sandbox
from ..records.store import read, write_once, lock


def execute(root):
    root = Path(root)
    spec = read(root / "spec.json")
    sandbox = Sandbox(**spec["sandbox"])
    started = time.monotonic()

    def limits():
        resource.setrlimit(
            resource.RLIMIT_AS, (sandbox.memory_bytes, sandbox.memory_bytes)
        )
        resource.setrlimit(
            resource.RLIMIT_FSIZE, (sandbox.file_bytes, sandbox.file_bytes)
        )
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    result = {"exit_code": None, "termination": "launch_error", "elapsed_seconds": 0}
    child = None
    try:
        with (
            (root / "stdout.log").open("xb") as stdout,
            (root / "stderr.log").open("xb") as stderr,
        ):
            child = subprocess.Popen(
                sandbox.command(root / "case", spec["argv"]),
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                env={"PATH": "/usr/bin:/bin"},
                preexec_fn=limits,
            )
            write_once(
                root / "child.json",
                {
                    "pid": child.pid,
                    "boot_id": Path("/proc/sys/kernel/random/boot_id")
                    .read_text()
                    .strip(),
                    "start_ticks": Path(f"/proc/{child.pid}/stat")
                    .read_text()
                    .rsplit(")", 1)[1]
                    .split()[19],
                },
            )
            reason = "exited"
            while child.poll() is None:
                if (root / "cancel.json").exists():
                    reason = "cancelled"
                elif spec["seconds"] is not None and time.monotonic() - started >= spec["seconds"]:
                    reason = "budget_exhausted"
                else:
                    time.sleep(0.05)
                    continue
                os.killpg(child.pid, signal.SIGKILL)
                break
            code = child.wait()
            result.update(exit_code=code, termination=reason)
            result["elapsed_seconds"] = time.monotonic() - started
            write_once(
                root / "exit.json", result
            )  # never rerun on log-collection failure
            stdout.flush()
            stderr.flush()
            os.fsync(stdout.fileno())
            os.fsync(stderr.fileno())
    except BaseException as exc:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        if not (root / "exit.json").exists():
            result.update(
                error_type=type(exc).__name__,
                message=str(exc),
                elapsed_seconds=time.monotonic() - started,
            )
            write_once(root / "exit.json", result)
    collect(root)


def collect(root):
    root = Path(root)
    with lock(root / "collect.lock"):
        return _collect(root)


def _collect(root):
    if (root / "result.json").exists():
        return read(root / "result.json")
    receipt = read(root / "exit.json")
    # A partial collection is not success; retry safely from the original case.
    frozen = root / "artifacts"
    if not frozen.exists():
        # Interrupted copies are audit evidence, never published partial results.
        staging = root / ("collection-" + uuid.uuid4().hex)
        snapshot(root / "case", staging)
        staging.rename(frozen)
    hashes = inventory(frozen)
    if hashes != inventory(root / "case"):
        raise RuntimeError("Incomplete artifact collection")
    for name in ("stdout.log", "stderr.log"):
        hashes["@" + name] = (
            __import__("hashlib").sha256((root / name).read_bytes()).hexdigest()
        )
    result = {
        **receipt,
        "run_id": root.name,
        "kind": read(root / "spec.json")["kind"],
        "lifecycle": "completed",
        "artifacts": hashes,
        "success": receipt["exit_code"] == 0 and receipt["termination"] == "exited",
    }
    write_once(root / "result.json", result)
    return result


if __name__ == "__main__":
    execute(sys.argv[1])
