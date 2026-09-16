"""One YAML, frozen before execution. Credentials are referenced, never copied."""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid
import hashlib
import yaml

from .loader import Task
from ..execution.files import inventory
from ..execution.sandbox import Sandbox
from ..execution.identity import verify_runtime
from ..records.store import read, write_once, digest
from ..harnesses.research import facts as research_facts


def harness_identity(config=None):
    from ..harnesses.codex import CODEX, BWRAP

    result = {}
    paths = [("codex", CODEX), ("bwrap", BWRAP)]
    if config and config["harness"]["name"] == "kimi-code":
        from ..harnesses.kimi import runtime_identity
        result["kimi-code"] = runtime_identity(config["harness"]["runtime"])
        paths = [("node", Path("/usr/bin/node")), ("bwrap", BWRAP)]
    for name, path in paths:
        with path.open("rb") as stream:
            result[name] = {
                "path": str(path),
                "sha256": hashlib.file_digest(stream, "sha256").hexdigest(),
            }
    return result


def load(path):
    path = Path(path).resolve()
    config = yaml.safe_load(path.read_text())
    if config.get("version") != "workbench-v3":
        raise ValueError("Use a workbench-v3 experiment; old runs stay archived")
    if config["harness"]["name"] not in ("codex", "kimi-code"):
        raise ValueError("Select an implemented CLI bridge: codex or kimi-code")
    if config["harness"].get("reasoning_effort") == "ultra":
        raise ValueError("This experiment disables delegation; select xhigh or lower")
    if not isinstance(config["model"], str) or not config["model"]:
        raise ValueError("An explicit model is required")
    for key in ("model_calls", "native_seconds", "request_seconds"):
        if key == "native_seconds" and config["budget"][key] is None:
            continue  # Explicitly unlimited; never encode infinity in receipts.
        if type(config["budget"][key]) is not int or config["budget"][key] <= 0:
            raise ValueError("Positive budgets required")
    if set(config["budget"]) != {"model_calls", "native_seconds", "request_seconds"}:
        raise ValueError("No implicit token/fee/submission limits")
    completion = config.get("completion", {})
    if not isinstance(completion, dict) or set(completion) - {"on_model_budget_exhausted"}:
        raise ValueError("Unknown completion policy")
    if completion.get("on_model_budget_exhausted", "require_submission") not in (
        "require_submission", "evaluate_latest_successful",
    ):
        raise ValueError("Unknown completion policy")
    base = path.parent
    if config["harness"]["name"] == "kimi-code":
        from ..harnesses.kimi import validate_settings
        settings = config["harness"]
        for key in ("runtime", "env_file"):
            if settings.get(key):
                settings[key] = str((base / settings[key]).resolve())
        validate_settings(settings)
    for key in ("task_root", "docs", "output"):
        config[key] = str((base / config[key]).resolve())
    if config["execution"].get("foam_root"):
        config["execution"]["foam_root"] = str(
            (base / config["execution"]["foam_root"]).resolve()
        )
    tasks = [Task.load(Path(config["task_root"]) / name) for name in config["tasks"]]
    if len({t.task_id for t in tasks}) != len(tasks):
        raise ValueError("Duplicate task registrations")
    from ..harnesses.research import live
    live(config)  # Validate the explicit research mode; no implicit network grant.
    if not Path(config["docs"]).is_dir():
        raise ValueError("Frozen offline documentation directory missing")
    return config, tasks


def prepare(path):
    config, tasks = load(path)
    runtime = Sandbox(**config["execution"])
    isolation = runtime.probe()
    blockers = []
    warnings = []
    if config["harness"]["name"] == "kimi-code":
        from ..harnesses.kimi import credentials
        try:
            harness_identity(config)
            credentials(config["harness"])
        except (ValueError, OSError, KeyError) as exc:
            blockers.append(str(exc))
    if not runtime.foam_root:
        blockers.append("OpenFOAM runtime missing")
    manifest = Path(config["docs"]) / "manifest.json"
    if not manifest.exists() or read(manifest).get("coverage_reviewed") is not True:
        blockers.append("Offline documentation coverage not reviewed")
    else:
        files = inventory(config["docs"])
        files.pop("manifest.json", None)
        if read(manifest).get("content_identity") != digest(files):
            blockers.append("Offline documentation changed since coverage audit")
    runtime_manifest = Path(runtime.foam_root or ".") / "workbench-manifest.json"
    if (
        not runtime_manifest.exists()
        or read(runtime_manifest).get("native_integration_passed") is not True
    ):
        blockers.append("Native image integration not qualified")
    else:
        try:
            verify_runtime(runtime.foam_root)
        except ValueError as exc:
            blockers.append(str(exc))
    engineering_ready = not blockers
    for task in tasks:
        target, grading = task.private()
        from ..grading.qualification import validate
        try:
            validate(task,target,grading)
        except (ValueError,OSError,KeyError) as exc:
            blockers.append(task.task_id+": "+str(exc))
        if grading.get("policy") == "dense-observation-v1" and (
            grading.get("release_status") != "released"
            or grading.get("rubric_approved") is not True
        ):
            blockers.append(task.task_id + ": dense reconstruction draft; rubric and integrity review not released")
        if grading.get("general_mesh_qualified") is not True:
            blockers.append(
                task.task_id
                + ": unrestricted-mesh grader not qualified; never count unsupported meshes as model failures"
            )
        if grading.get("policy") == "dense-observation-v1":
            warnings.append(task.task_id + ": public dense target; raw reconstruction metrics do not prove mechanism identification or convergence")
        elif not grading.get("convergence_rules"):
            warnings.append(
                task.task_id
                + ": preserves expert-accepted finite GT policy; convergence diagnostics are not new scoring gates"
            )
    return {
        "schema": "preparation-v3",
        "research": research_facts(config),
        "tasks": [t.task_id for t in tasks],
        "isolation": isolation,
        "engineering_ready": engineering_ready,
        "blockers": blockers,
        "warnings": warnings,
        "ready": not blockers,
        "paid_calls": 0,
    }


def archive(path):
    config, tasks = load(path)
    root = Path(config["output"]) / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    root.mkdir(parents=True, exist_ok=False)
    write_once(root / "experiment.json", config)
    shutil.copyfile(path, root / "experiment.yaml")
    # All code/public/private/docs snapshots remain HOST-owned; only public/ is mounted.
    shutil.copytree(
        Path(__file__).resolve().parents[1],
        root / "code/agentcfd_bench",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(config["docs"], root / "docs")
    for task in tasks:
        shutil.copytree(task.root, root / "tasks" / task.task_id)
        (root / "trials" / task.task_id).mkdir(parents=True)
    write_once(
        root / "identity.json",
        {
            "code": digest(inventory(root / "code")),
            "docs": digest(inventory(root / "docs")),
            "tasks": {t.task_id: t.identity for t in tasks},
            "harness": harness_identity(config),
            "native_manifest": (
                read(Path(config["execution"]["foam_root"]) / "workbench-manifest.json")
                if config["execution"].get("foam_root")
                else None
            ),
        },
    )
    return root
