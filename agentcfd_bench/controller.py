"""One clear orchestration loop. Native tasks and model turns have durable IDs."""

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

from .tasks.experiment import prepare, archive, harness_identity
from .tasks.loader import Task
from .execution.runner import Runner
from .execution.sandbox import Sandbox
from .execution.identity import verify_runtime
from .execution.files import inventory
from .records.store import Store, read, write_once, digest, lock
from .harnesses.codex import Codex, protocol_for
from .reports.summary import report
from . import finalization


def status_file(path, value):
    # Replaceable UI projection only; immutable receipts + SQLite are authoritative.
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def run(experiment):
    qualification = prepare(experiment)
    if not qualification["ready"]:
        raise RuntimeError(
            "Preparation blocked: " + ", ".join(qualification["blockers"])
        )
    root = archive(experiment)
    write_once(root / "preparation.json", qualification)
    return frozen_resume(root)


def frozen_resume(root):
    """CLI execution always uses the run's snapshot, including the initial launch."""
    root = Path(root).resolve(strict=True)
    import subprocess

    command = [
        sys.executable,
        "-B",
        "-m",
        "agentcfd_bench",
        "resume",
        str(root),
        "--allow-paid",
    ]
    environment = {
        **os.environ,
        "PYTHONPATH": str(root / "code"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    subprocess.run(command, cwd=root / "code", env=environment, check=True)
    return report(root)


def resume(root, *, agent_class=None):
    root = Path(root).resolve(strict=True)
    config = read(root / "experiment.json")
    if agent_class is None:
        if config["harness"]["name"] == "kimi-code":
            from .harnesses.kimi import KimiCode
            agent_class = KimiCode
        elif config["harness"]["name"] == "codex":
            agent_class = Codex
        else:
            raise ValueError("Unknown frozen harness")
    identity = read(root / "identity.json")
    if (
        digest(inventory(root / "code")) != identity["code"]
        or digest(inventory(root / "docs")) != identity["docs"]
    ):
        raise ValueError("Frozen code or documentation changed")
    # No silently changed implementation on resume. CLI below uses the frozen copy.
    current = Path(__file__).resolve().parent
    current_identity = digest(
        {
            k: v
            for k, v in inventory(current).items()
            if "__pycache__" not in k and not k.endswith(".pyc")
        }
    )
    frozen_identity = digest(
        {
            k.removeprefix("agentcfd_bench/"): v
            for k, v in inventory(root / "code").items()
        }
    )
    if current_identity != frozen_identity:
        raise ValueError("Use this run's frozen code to resume")
    if harness_identity(config) != identity["harness"]:
        raise ValueError("Pinned CLI or sandbox binary changed")
    if config["execution"].get("foam_root"):
        verify_runtime(config["execution"]["foam_root"], identity["native_manifest"])
    with lock(root / "controller.lock"):
        for task_id in config["tasks"]:
            trial = root / "trials" / task_id
            db = Store(trial)
            state = db.get(
                "trial",
                {
                    "lifecycle": "queued",
                    "verdict": "not_evaluated",
                    "calls": 0,
                    "session": None,
                },
            )
            if state["lifecycle"] == "completed":
                continue
            if state.get("request_inflight"):
                # Reconcile a saved response; NEVER redispatch unknown model requests.
                receipts = sorted((trial / "calls").glob("turn-*/result.json"))
                saved = receipts[-1] if receipts else None
                if saved and str(saved) != state.get("last_response"):
                    result = read(saved)
                    state.update(
                        calls=state["calls"] + result["calls"],
                        session=result["session"],
                        request_inflight=False,
                        last_response=str(saved),
                    )
                    if finalization.enabled(config) and state["calls"] >= config["budget"]["model_calls"]:
                        state["terminal_model_result"] = {
                            key: result.get(key) for key in
                            ("errors", "exit_code", "completed", "budget_exhausted")
                        }
                    if (
                        result["errors"]
                        or result["exit_code"]
                        or not result["completed"]
                    ):
                        state.update(
                            lifecycle="interrupted",
                            verdict="error",
                            reason="model_transport_error",
                        )
                    db.set("trial", state, event="response_recovered")
                else:
                    state.update(
                        lifecycle="interrupted",
                        verdict="error",
                        reason="model_request_outcome_unresolved",
                    )
                    db.set("trial", state, event="request_unresolved")
                    status_file(trial / "status.json", state)
                    continue
            exhausted = state["calls"] >= config["budget"]["model_calls"]
            if (state.get("reason") == "model_transport_error"
                    and not (finalization.enabled(config) and exhausted)
                    and not (trial / "submission.json").exists()):
                continue
            task = Task.load(root / "tasks" / task_id)
            if task.identity != identity["tasks"][task_id]:
                raise ValueError("Frozen task changed")
            runner = Runner(
                trial / "native",
                Sandbox(**config["execution"]),
                seconds=config["budget"]["native_seconds"],
            )
            agent = None
            prompt = (
                task.public_prompt()
                + "\n"
                + protocol_for(task, config)
                + "\nTotal budgets: "
                + json.dumps(config["budget"])
                + "\n" + finalization.protocol(config)
                + "\nGeometry: /input/geometry/"
            )
            while (
                not (trial / "submission.json").exists()
                and state["calls"] < config["budget"]["model_calls"]
            ):
                state.update(
                    lifecycle="running", request_inflight=True, verdict="not_evaluated"
                )
                db.set("trial", state, event="model_dispatch_intent")
                status_file(trial / "status.json", state)
                try:
                    if agent is None:
                        agent = agent_class(
                            trial, config, runner, task.root / "public", root / "docs"
                        )
                    result = agent.run(
                        prompt,
                        config["budget"]["model_calls"] - state["calls"],
                        session=state["session"],
                    )
                except Exception as exc:
                    state.update(
                        lifecycle="interrupted",
                        verdict="error",
                        reason="model_request_outcome_unresolved",
                        error_type=type(exc).__name__,
                    )
                    db.set("trial", state, event="model_interrupted")
                    break
                saved = sorted((trial / "calls").glob("turn-*/result.json"))[-1]
                state.update(
                    calls=state["calls"] + result["calls"],
                    session=result["session"],
                    request_inflight=False,
                    last_response=str(saved),
                )
                db.set("trial", state, event="model_response_recorded")
                if (finalization.enabled(config)
                        and state["calls"] >= config["budget"]["model_calls"]):
                    # A CLI can exit nonzero when our broker refuses call N+1.
                    # A saved receipt still accounts for N real calls. Preserve
                    # actual transport diagnostics separately from physical score.
                    state["terminal_model_result"] = {
                        key: result.get(key) for key in
                        ("errors", "exit_code", "completed", "budget_exhausted")
                    }
                    break
                if result["errors"] or result["exit_code"] or not result["completed"]:
                    state.update(
                        lifecycle="interrupted",
                        verdict="error",
                        reason="model_transport_error",
                    )
                    break
                if result["calls"] < 1:
                    state.update(
                        lifecycle="interrupted",
                        verdict="error",
                        reason="no_provider_progress",
                    )
                    break
                prompt = (
                    "Continue the SAME task. Your files and session persist. Inspect existing operations, then explicitly submit when ready. Remaining budgets: "
                    + json.dumps(
                        {
                            "model_calls": config["budget"]["model_calls"]
                            - state["calls"],
                            "native_seconds": runner.remaining(),
                        }
                    )
                )
            budget_handoff = (finalization.enabled(config)
                              and state["calls"] >= config["budget"]["model_calls"]
                              and not state.get("request_inflight"))
            selection = None
            if budget_handoff:
                state.update(lifecycle="running", verdict="not_evaluated",
                             phase="finalizing", stop_reason="model_budget_exhausted")
                state.pop("reason", None)
                db.set("trial", state, event="budget_finalization_started")
                status_file(trial / "status.json", state)
                try:
                    selection = finalization.select(trial, runner)
                    state.update(selected_run_id=selection["run_id"],
                                 selection_source=selection["source"])
                    db.set("trial", state, event="budget_result_selected")
                except Exception as exc:
                    state.update(lifecycle="interrupted", verdict="error",
                                 reason="finalization_evidence_unresolved",
                                 error_type=type(exc).__name__, detail=str(exc))
                    db.set("trial", state, event="finalization_interrupted")
                    status_file(trial / "status.json", state)
                    continue
            selected_run_id = (selection["run_id"] if selection else
                               read(trial / "submission.json")["run_id"]
                               if (trial / "submission.json").exists() else None)
            if selected_run_id:
                from .grading.service import grade_submission

                try:
                    outcome = grade_submission(
                        task,
                        runner,
                        selected_run_id,
                        trial / "grading",
                    )
                    if budget_handoff:
                        finalization.record_summary(trial, state, selection, outcome)
                    state.update(
                        lifecycle="completed",
                        phase="finished",
                        verdict=outcome["verdict"],
                        reason=outcome["reason"],
                    )
                except Exception as exc:
                    state.update(
                        lifecycle="interrupted",
                        verdict="error",
                        reason="grading_interrupted",
                        error_type=type(exc).__name__,
                    )
            elif (not state.get("request_inflight")
                  and state["calls"] >= config["budget"]["model_calls"]):
                reason = "no_successful_native_output" if budget_handoff else "model_budget_exhausted"
                state.update(
                    lifecycle="completed",
                    phase="finished",
                    verdict="fail",
                    reason=reason,
                )
                outcome = {'verdict':'fail', 'reason':reason}
                _, policy = task.private()
                if policy.get('policy') == 'dense-observation-v1' and policy.get('release_status') == 'released':
                    from .grading.dense_native import publish_reward
                    outcome = {'verdict':'fail', 'reason':reason,
                               'reward':0.0, 'reward_version':policy['rubric']['version'],
                               'integrity_review_required':False}
                    grading = trial / 'grading'
                    if (grading / 'result.json').exists():
                        if read(grading / 'result.json') != outcome:
                            raise RuntimeError('Budget outcome differs from recorded grading')
                    else:
                        write_once(grading / 'result.json', outcome)
                    publish_reward(grading, outcome, policy)
                if budget_handoff:
                    finalization.record_summary(trial, state, selection, outcome)
            db.set("trial", state, event="trial_observed")
            status_file(trial / "status.json", state)
    return report(root)
