"""Run identity, budget reservations, polling and recovery. No physics scoring."""

from dataclasses import asdict
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from .files import snapshot, inventory
from .worker import collect
from ..records.store import read, write_once, lock


class Runner:
    def __init__(self, root, sandbox, *, seconds=1000):
        if seconds is not None and (type(seconds) not in (int, float)
                                    or not math.isfinite(seconds) or seconds <= 0):
            raise ValueError("Runtime budget must be positive or null (unlimited)")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sandbox, self.seconds = sandbox, seconds
        config = {"sandbox": asdict(sandbox), "seconds": seconds}
        if (self.root / "runtime.json").exists():
            if read(self.root / "runtime.json") != config:
                raise ValueError("Cannot resume with a changed runtime/budget")
        else:
            write_once(self.root / "runtime.json", config)

    def directory(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"r-[a-f0-9]{16}", run_id):
            raise ValueError("Invalid run identifier")
        path = self.root / run_id
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Unknown run")
        return path

    def remaining(self):
        if self.seconds is None:
            return None
        spent = 0
        for root in self.root.glob("r-*"):
            if (root / "exit.json").exists():
                spent += read(root / "exit.json")["elapsed_seconds"]
            elif (root / "dispatch.json").exists():
                spent += read(root / "spec.json")[
                    "seconds"
                ]  # unknown outcomes keep reservation
        return max(0, self.seconds - spent)

    def start(self, work, argv, *, kind="exec", seconds=None):
        if seconds is not None and (type(seconds) not in (int, float)
                                    or not math.isfinite(seconds) or seconds <= 0):
            raise ValueError("Invalid requested runtime")
        if kind not in ("exec", "run"):
            raise ValueError("Expected exec or run")
        if kind == "run":
            # All installed native executables are selectable, not a solver allowlist.
            if not self.sandbox.foam_root:
                raise RuntimeError("OpenFOAM runtime not configured")
            if not argv or not re.fullmatch(r"[A-Za-z0-9_.+-]+", argv[0]):
                raise ValueError(
                    "run takes an installed native executable name; use exec for scripts"
                )
            program = Path(self.sandbox.foam_root) / "bin" / argv[0]
            if not program.is_file():
                raise ValueError("Native executable not installed: " + argv[0])
            argv = ["/opt/foam/bin/" + argv[0], *argv[1:]]
        with lock(self.root / "dispatch.lock"):
            for running in self.root.glob("r-*"):
                if (running / "dispatch.json").exists() and not (
                    running / "exit.json"
                ).exists():
                    raise RuntimeError(
                        "Observe the existing operation before starting another"
                    )
            remaining = self.remaining()
            if remaining is not None and remaining <= 0:
                raise ValueError("Native runtime budget exhausted")
            allowance = seconds if remaining is None else min(
                remaining, seconds if seconds is not None else remaining
            )
            # Allocate under the dispatch lock. UUIDs and filesystem mtimes do
            # not define experiment order, especially after recovery/copying.
            sequence = len(list(self.root.glob("r-*"))) + 1
            root = self.root / ("r-" + uuid.uuid4().hex[:16])
            root.mkdir()
            # A solver can modify its working copy. Retain the actual submitted
            # inputs as well as their hashes, so initialization/restart provenance
            # can be audited after completion. Never infer them from final fields.
            if kind == "run":
                inputs = snapshot(work, root / "inputs")
                snapshot(root / "inputs", root / "case")
            else:
                inputs = snapshot(work, root / "case")
            write_once(
                root / "spec.json",
                {
                    "argv": list(argv),
                    "kind": kind,
                    "seconds": allowance,
                    "inputs": inputs,
                    "input_evidence": kind == "run",
                    "sandbox": asdict(self.sandbox),
                },
            )
            write_once(root / "dispatch.json", {"state": "dispatch_intent", "sequence": sequence})
            try:
                self.dispatch_worker(root)
            except OSError as exc:
                write_once(
                    root / "exit.json",
                    {
                        "exit_code": None,
                        "termination": "launch_error",
                        "elapsed_seconds": 0,
                        "error_type": type(exc).__name__,
                    },
                )
                raise
            return {
                "run_id": root.name,
                "lifecycle": "running",
                "seconds_reserved": allowance,
            }

    def dispatch_worker(self, root, module="agentcfd_bench.execution.worker"):
        """Transport hook; the default local worker and its protocol are unchanged."""
        with (root / "worker.log").open("xb") as log:
            child = subprocess.Popen(
                [sys.executable, "-m", module, str(root)], stdout=log, stderr=log,
                stdin=subprocess.DEVNULL, start_new_session=True,
                cwd=Path(__file__).resolve().parents[2],
                env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            write_once(root / "worker.json", {
                "pid": child.pid,
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "start_ticks": Path(f"/proc/{child.pid}/stat").read_text().rsplit(")", 1)[1].split()[19],
            })

    def status(self, run_id):
        root = self.directory(run_id)
        if (root / "result.json").exists():
            return read(root / "result.json")
        if (root / "exit.json").exists():
            return collect(root)
        # Never infer a successful exit or automatically replace an unknown job.
        worker = read(root / "worker.json") if (root / "worker.json").exists() else {}
        alive = False
        if worker.get("pid"):
            try:
                fields = (
                    Path(f"/proc/{worker['pid']}/stat")
                    .read_text()
                    .rsplit(")", 1)[1]
                    .split()
                )
                alive = (
                    fields[0] != "Z"
                    and fields[19] == worker.get("start_ticks")
                    and worker.get("boot_id")
                    == Path("/proc/sys/kernel/random/boot_id").read_text().strip()
                )
            except (OSError, IndexError):
                pass
        return {
            "run_id": run_id,
            "lifecycle": "running" if alive else "interrupted",
            "reason": "execution_in_progress" if alive else "exit_evidence_missing",
        }

    def cancel(self, run_id):
        root = self.directory(run_id)
        if not (root / "cancel.json").exists():
            write_once(root / "cancel.json", {"requested": True})
        return self.status(run_id)

    def logs(self, run_id, *, stream="stdout", offset=0, size=16000):
        if (
            stream not in ("stdout", "stderr")
            or type(offset) is not int
            or offset < 0
            or type(size) is not int
            or not 1 <= size <= 1000000
        ):
            raise ValueError("Invalid log range")
        path = self.directory(run_id) / (stream + ".log")
        if not path.exists():
            return {"text": "", "next_offset": offset}
        with path.open("rb") as file:
            file.seek(offset)
            data = file.read(size)
        return {
            "text": data.decode(errors="replace"),
            "next_offset": offset + len(data),
        }

    def verify(self, run_id):
        root = self.directory(run_id)
        result = self.status(run_id)
        if result["lifecycle"] != "completed":
            raise RuntimeError("Run has no terminal evidence")
        actual = inventory(root / "artifacts")
        import hashlib

        for name in ("stdout.log", "stderr.log"):
            actual["@" + name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != result["artifacts"]:
            raise RuntimeError("Native output evidence changed")
        spec = read(root / "spec.json")
        if spec.get("input_evidence") and inventory(root / "inputs") != spec["inputs"]:
            raise RuntimeError("Native input evidence changed")
        return root, result
