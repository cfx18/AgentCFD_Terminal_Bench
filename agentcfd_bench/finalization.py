"""Deterministic budget-end handoff. No model calls and no GT-based selection."""

import time

from .records.store import read, write_once


POLICY = "evaluate_latest_successful"


def enabled(config):
    return config.get("completion", {}).get("on_model_budget_exhausted") == POLICY


def protocol(config):
    parts = []
    if config["budget"]["native_seconds"] is None:
        parts.append(
            "Native-time budget is unlimited (null): there is no task wall-clock "
            "or cumulative native execution deadline. You may optionally request "
            "a timeout for an individual command. API no-response watchdogs, memory "
            "and file-size safety limits still apply."
        )
    if enabled(config):
        parts.append(
            "At the model-call limit, no further model call is made (including for "
            "summarization). Your explicit submission takes priority. Otherwise the "
            "controller waits for already dispatched native work, then automatically "
            "evaluates your latest successfully exited native run, in dispatch order, "
            "not the best GT match. Failed/cancelled runs and preparation commands are "
            "not fallback candidates. Saved fields, not natural-language claims, "
            "are graded by the normal evaluator; partial reward is retained. A short "
            "diagnostic run is not exempt from the normal physical endpoint checks."
        )
    return "\n".join(parts)


def select(trial, runner):
    """Freeze once; on resume observe existing jobs, never dispatch replacements.

    Caller persists its finalizing phase before entry. Unlimited jobs may require
    external cancellation if genuinely hung. Missing exit evidence is an error,
    not permission to silently choose an older answer or invent a zero score.
    """
    receipt = trial / "finalization/selection.json"
    if receipt.exists():
        return read(receipt)
    submission = trial / "submission.json"
    if submission.exists():
        run_id = read(submission)["run_id"]
        runner.verify(run_id)
        selection = {"source": "agent_submission", "run_id": run_id}
    else:
        ordered = []
        for path in runner.root.glob("r-*/dispatch.json"):
            sequence = read(path).get("sequence")
            if type(sequence) is not int or sequence <= 0:
                raise RuntimeError("Native dispatch order missing; cannot select by guessing")
            ordered.append((sequence, path.parent.name))
        ordered.sort()
        if len({seq for seq, _ in ordered}) != len(ordered):
            raise RuntimeError("Ambiguous native dispatch order")
        observations = []
        chosen = None
        for sequence, run_id in ordered:
            while True:
                result = runner.status(run_id)  # Collect an existing exit receipt.
                if result["lifecycle"] != "running":
                    break
                time.sleep(0.1)
            if result["lifecycle"] != "completed" or result["termination"] == "launch_error":
                raise RuntimeError("Native execution evidence unresolved: " + run_id)
            observations.append({
                "sequence": sequence, "run_id": run_id, "kind": result["kind"],
                "success": result["success"], "termination": result["termination"],
                "elapsed_seconds": result["elapsed_seconds"],
            })
            if result["kind"] == "run" and result["success"]:
                chosen = run_id
        if chosen:
            runner.verify(chosen)
        selection = {
            "source": "budget_fallback", "policy": POLICY, "run_id": chosen,
            "reason": "latest_successful_native_run" if chosen else "no_successful_native_output",
            "operations": observations,
        }
    write_once(receipt, selection)
    return selection


def record_summary(trial, state, selection, outcome):
    """An audit summary, NOT an extra Agent answer or fabricated reasoning."""
    path = trial / "finalization/summary.json"
    value = {
        "schema": "budget-finalization-v1", "model_calls": state["calls"],
        "additional_model_calls": 0, "selection": selection,
        "transcript": "transcript.jsonl", "grading": outcome,
        "stop_reason": "model_budget_exhausted",
    }
    if path.exists():
        if read(path) != value:
            raise RuntimeError("Finalization summary differs from recorded evidence")
    else:
        write_once(path, value)
