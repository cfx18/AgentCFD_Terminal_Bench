"""Explicit, audited regrading of an existing submission; never calls an Agent.

Original task/code snapshots, submissions and scores are not overwritten. Only
trusted measurement exports may be rerun (no solver time advancement). A new
receipt is committed before updating the replaceable scoreboard projection.
"""

from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import shutil
import uuid

from ..execution.files import inventory
from ..execution.identity import verify_runtime
from ..execution.runner import Runner
from ..execution.sandbox import Sandbox
from ..records.store import Store, digest, read, write_once
from ..tasks.loader import Task
from .qualification import grader_identity
from .service import grade_submission


def regrade(root, task_id):
    root = Path(root).resolve(strict=True)
    config = read(root / "experiment.json")
    if task_id not in config["tasks"] or Path(task_id).name != task_id:
        raise ValueError("Select a registered task ID")
    # Never hot-patch or compete with a live evaluation controller.
    with (root / "controller.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Stop or finish the controller before regrading") from None
        trial = root / "trials" / task_id
        if not (trial / "state.sqlite").exists():
            raise ValueError("Trial has not run")
        db = Store(trial)
        before = db.get("trial", {})
        if before.get("lifecycle") != "completed" or before.get("request_inflight"):
            raise ValueError("Only a completed trial can be regraded")
        submission_path = trial / "submission.json"
        if not submission_path.exists():
            from ..finalization import enabled
            submission_path = trial / "finalization/selection.json"
            if not enabled(config) or not submission_path.exists():
                raise ValueError("No explicit submission or frozen budget selection; do not choose an answer for the Agent")
            selected = read(submission_path)
            if (not selected.get("run_id") or selected["run_id"] != before.get("selected_run_id")
                    or before.get("stop_reason") != "model_budget_exhausted"):
                raise ValueError("Budget selection does not match the completed trial")
        submission = read(submission_path)
        identity = read(root / "identity.json")
        task = Task.load(root / "tasks" / task_id)
        if task.identity != identity["tasks"][task_id]:
            raise ValueError("Frozen task changed")
        verify_runtime(config["execution"]["foam_root"], identity["native_manifest"])
        runner = Runner(trial / "native", Sandbox(**config["execution"]),
                        seconds=config["budget"]["native_seconds"])
        native, evidence = runner.verify(submission["run_id"])
        if evidence["kind"] != "run":
            raise ValueError("Submission is not a solver run")

        now = datetime.now(timezone.utc)
        revision = trial / "regrades" / (now.strftime("%Y%m%dT%H%M%S.%fZ-") + uuid.uuid4().hex[:8])
        revision.mkdir(parents=True)
        source = Path(__file__).resolve().parent
        code_id = grader_identity()
        source_files = {k: v for k, v in inventory(source).items()
                        if "__pycache__" not in Path(k).parts and not k.endswith(".pyc")}
        shutil.copytree(source, revision / "grader-code",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        code_files = inventory(revision / "grader-code")
        if code_files != source_files:
            raise RuntimeError("Grading code changed while snapshotting")
        original = read(trial / "grading/result.json") if (trial / "grading/result.json").exists() else None
        receipt = {
            "time": now.isoformat(), "task_id": task_id,
            "source_state": before, "original_grade": original,
            "submission": submission, "task_identity": task.identity,
            "native_result_identity": digest(evidence),
            "grader_identity": code_id, "grader_code_files": code_files,
            "model_calls_added": 0, "solver_runs_added": 0,
        }
        write_once(revision / "intent.json", receipt)
        result = grade_submission(task, runner, submission["run_id"], revision)
        # The existing grading service atomically writes its own result receipt.
        if read(revision / "result.json") != result:
            raise RuntimeError("Grading result receipt mismatch")
        task.private()  # revalidate frozen task contents, including the GT
        if (grader_identity() != code_id
                or inventory(revision / "grader-code") != code_files
                or read(submission_path) != submission
                or digest(runner.verify(submission["run_id"])[1]) != digest(evidence)):
            raise RuntimeError("Grading code, task or submission changed during regrade")
        if db.get("trial") != before:
            raise RuntimeError("Trial state changed during regrade")
        pointer = (revision / "result.json").relative_to(trial).as_posix()
        after = {**before, "verdict": result["verdict"], "reason": result["reason"],
                 "grading_result": pointer, "regraded_at": now.isoformat()}
        write_once(revision / "commit.json", {
            "result_identity": digest(result), "state_before": before, "state_after": after,
        })
        db.set("trial", after, event="submission_regraded")
        # UI projection only; SQLite + immutable receipts remain authoritative.
        temporary = trial / "status.regrade.tmp"
        temporary.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(trial / "status.json")
        return {"task": task_id, "revision": str(revision),
                "previous_verdict": before.get("verdict"), "result": result}
