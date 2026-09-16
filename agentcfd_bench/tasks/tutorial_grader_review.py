"""Structured review gates for tutorial grader release candidates."""

from __future__ import annotations


FATAL_KEYWORDS = (
    "formal metric grader unavailable",
    "not a reliable formal ground truth",
    "unresolved physical-admissibility defect",
    "contradict",
    "no native reference field",
    "not produced or replayed by a native openfoam export",
    "does not contain the cited native",
    "not bundled",
    "interrupted before execution",
)

REVIEW_KEYWORDS = (
    "mesh-convergence",
    "not mesh-independent",
    "not stationary",
    "transient",
    "finite numerical",
    "human acceptance",
    "expert acceptance",
    "not approved",
    "unapproved",
    "threshold",
    "calibrated",
    "provisional",
)


def classify_blocker(text: str) -> str:
    lower = text.lower()
    if any(key in lower for key in FATAL_KEYWORDS):
        return "fatal"
    if any(key in lower for key in REVIEW_KEYWORDS):
        return "review"
    return "review"


def review_record(task_id: str, readiness: dict, author: dict, policy: dict) -> dict:
    blockers = list(policy.get("blockers") or readiness.get("blockers") or [])
    gates = {
        "query_ok": readiness.get("query_ok") is True,
        "input_complete": readiness.get("input_complete") is True,
        "gt_available": readiness.get("gt_available") is True,
        "metric_grader_executable": policy.get("metric_grader_executable") is True,
        "has_scored_fields": bool(policy.get("fields")),
        "has_reward_anchors": bool(policy.get("full_credit") and policy.get("zero_credit")),
    }
    classified = [
        {"severity": classify_blocker(blocker), "text": blocker}
        for blocker in blockers
    ]
    fatal_count = sum(1 for item in classified if item["severity"] == "fatal")
    if not all(gates.values()):
        decision = "blocked"
    elif fatal_count:
        decision = "blocked"
    elif classified or readiness.get("publish_ready") is not True:
        decision = "review"
    else:
        decision = "released_candidate"
    return {
        "schema": "tutorial-grader-review-v1",
        "task_id": task_id,
        "decision": decision,
        "gates": gates,
        "blockers": classified,
        "warnings": readiness.get("warnings") or [],
        "llm_material_used": {
            "readiness_file": "private/release-readiness.json",
            "author_result": "private/author-result.json",
            "draft_rubric": "public/rubric.json",
        },
        "deterministic_guardrail": (
            "LLM/draft rubric may suggest fields and blocker severity, but cannot set "
            "release_status=released unless all gates pass and blockers are absent."
        ),
        "author_status": author.get("status"),
        "observed_endpoint": author.get("observed_endpoint"),
        "scored_fields": sorted(policy.get("fields") or {}),
    }
