from pathlib import Path
import json
import sqlite3
from ..records.store import read


def report(root):
    root = Path(root)
    rows = []
    for trial in sorted((root / "trials").glob("*")):
        state = {"lifecycle": "queued", "verdict": "not_evaluated"}
        if (trial / "state.sqlite").exists():
            with sqlite3.connect(
                (trial / "state.sqlite").resolve().as_uri() + "?mode=ro", uri=True
            ) as db:
                row = db.execute("SELECT value FROM state WHERE key='trial'").fetchone()
                if row:
                    state = json.loads(row[0])
        native = [read(p) for p in (trial / "native").glob("r-*/result.json")]
        stats = {
            "native_commands": len(native),
            "solver_runs": sum(r["kind"] == "run" for r in native),
            "native_command_failures": sum(
                not r["success"] and r["termination"] == "exited" for r in native
            ),
            "native_timeouts": sum(
                r["termination"] == "budget_exhausted" for r in native
            ),
            "native_launch_errors": sum(
                r["termination"] == "launch_error" for r in native
            ),
            "native_seconds": sum(r["elapsed_seconds"] for r in native),
        }
        grading = trial / state.get('grading_result', 'grading/result.json')
        if not grading.resolve().is_relative_to(trial.resolve()):
            raise ValueError("Grading result must be inside its trial")
        if grading.exists():
            value = read(grading)
            stats.update(reward=value.get('reward'), reward_version=value.get('reward_version'),
                         metric_reward=value.get('metric_reward'), eligibility=value.get('eligibility', 'unknown'),
                         field_scores=value.get('field_scores'), metrics=value.get('metrics'),
                         integrity_review_required=value.get('integrity_review_required',False),
                         needs_expert_review=value.get('needs_expert_review',False))
        rows.append({"task": trial.name, **state, **stats})
    rewards = [r['reward'] for r in rows if r.get('reward') is not None]
    metric_rewards = [r['metric_reward'] for r in rows if r.get('metric_reward') is not None]
    return {
        "run_id": root.name,
        "research_mode": read(root / "experiment.json").get("network", "disabled")
        if (root / "experiment.json").exists() else "unknown",
        "tasks": rows,
        "registered": len(rows),
        "passed": sum(row.get("verdict") == "pass" for row in rows),
        "failed": sum(row.get("verdict") == "fail" for row in rows),
        "errors": sum(row.get("verdict") == "error" for row in rows),
        "review_required": sum(bool(row.get('integrity_review_required')) for row in rows),
        "reward_denominator": len(rewards),
        "mean_reward_scored": sum(rewards) / len(rewards) if rewards else None,
        "metric_reward_count": len(metric_rewards),
        "mean_metric_reward_diagnostic": sum(metric_rewards) / len(metric_rewards) if metric_rewards else None,
        "eligibility_counts": {key: sum(row.get('eligibility', 'unknown') == key for row in rows)
                               for key in ('eligible', 'invalid', 'review', 'error', 'unknown')},
        "rates_are_final": bool(rows)
        and all(row.get("lifecycle") == "completed" and row.get('verdict') in ('pass','fail') for row in rows),
    }


def markdown(root):
    result = report(root)
    lines = [
        "# 本轮评测状态",
        "",
        "资料访问条件：`" + result["research_mode"] + "`。联网与离线成绩不可混为同一条件。",
        "",
        "物理匹配分仅描述与 GT 的误差；正式 reward 还取决于有效性审计。待审／基础设施异常不记作 0 分。",
        "",
        "| 任务 | 生命周期 | 结果 | 有效性 | 物理匹配分 | 正式 reward | 原因 | 调用数 | 选取方式 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in result["tasks"]:
        lines.append(
            "| "
            + " | ".join(
                str(row[k]) if row.get(k) is not None else "—"
                for k in ("task", "lifecycle", "verdict", "eligibility", "metric_reward", "reward", "reason", "calls", "selection_source")
            )
            + " |"
        )
    for row in result["tasks"]:
        if row.get("stop_reason") == "model_budget_exhausted":
            lines.append(
                "\n" + row["task"] + "：调用耗尽后收尾，选中 `"
                + str(row.get("selected_run_id", "尚未选定"))
                + "`；评分独立于停止原因。审计摘要：`trials/"
                + row["task"] + "/finalization/summary.json`。"
            )
        if row.get("grading_result"):
            lines.append("\n重验收记录：`" + row["task"] + "/" + row["grading_result"] + "`（原评分保留）。")
    return "\n".join(lines) + "\n"
