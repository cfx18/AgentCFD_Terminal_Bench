"""Build a formal tutorial-grader release candidate from completed authoring output.

The command is deterministic, calls no model, and never marks a scientifically
blocked reference as a clean released benchmark. It publishes executable metric
policies plus the review state needed for a human release authority.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from ..grading.tutorial_metric import FULL_CREDIT, VERSION, ZERO_CREDIT
from ..records.store import digest, write_once
from .tutorial_grader_review import review_record


DEFAULT_GRADABLE_IDS = (
    "q-0051",
    "q-0064",
    "q-0094",
    "q-0131",
    "q-0146",
    "q-0176",
    "q-0291",
    "q-0505",
)

COORDS = {"cell_id", "x_m", "y_m", "z_m", "volume_m3", "cell_volume_m3"}

VECTOR_GROUPS = {
    "U": (("U_x", "U_y", "U_z"), ("U_x_m_per_s", "U_y_m_per_s", "U_z_m_per_s"), ("Ux_m_s", "Uy_m_s", "Uz_m_s")),
    "U.air": (("Uair_x_m_s", "Uair_y_m_s", "Uair_z_m_s"),),
    "Urel": (("Urelx_m_s", "Urely_m_s", "Urelz_m_s"),),
    "UMean": (("UMean_x", "UMean_y", "UMean_z"),),
}

SCALAR_ALIASES = {
    "T": ("T", "T_K"),
    "p": ("p", "p_Pa", "p_m2_per_s2"),
    "p_rgh": ("p_rgh", "p_rgh_m2_per_s2"),
    "rho": ("rho",),
    "b": ("b",),
    "ft": ("ft",),
    "Xi": ("Xi",),
    "k": ("k", "k_m2_s2", "k_m2_per_s2"),
    "epsilon": ("epsilon", "epsilon_m2_per_s3"),
    "omega": ("omega", "omega_s_1"),
    "nut": ("nut", "nut_m2_s", "nut_m2_per_s"),
    "alphat": ("alphat", "alphat_m2_per_s"),
    "Su": ("Su",),
    "St": ("St",),
    "Tu": ("Tu",),
    "kinematicCloud:theta": ("kinematicCloud:theta", "particle_theta"),
    "alpha.air": ("alpha.air", "alpha_air"),
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _csv_header(path: Path) -> list[str]:
    line = path.read_text(errors="ignore").splitlines()[0]
    return [x.strip() for x in line.split(",")]


def _observation_csv(public: Path) -> Path:
    candidates = [
        public / "observations" / "fields.csv",
        public / "observations" / "cell_fields.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise ValueError(f"No supported observation CSV under {public}")


def _wanted_fields_from_rubric(rubric: dict) -> list[str]:
    wanted: list[str] = []

    def add(name):
        if isinstance(name, str) and name and name not in wanted:
            wanted.append(name)

    target = rubric.get("target")
    if isinstance(target, dict):
        add(target.get("field"))
    for key in ("core_fields", "primary_fields", "scored_fields"):
        value = rubric.get(key)
        if isinstance(value, dict):
            for name in value:
                add(name)
        elif isinstance(value, list):
            for item in value:
                add(item.get("name") if isinstance(item, dict) else item)
    fields = rubric.get("fields")
    if isinstance(fields, dict):
        for name, spec in fields.items():
            role = str(spec.get("role", "")) if isinstance(spec, dict) else ""
            if "scored" in role and "diagnostic" not in role:
                add(name)
    return wanted


def _columns_for_field(name: str, header: list[str]) -> list[str] | None:
    header_set = set(header)
    if name in VECTOR_GROUPS:
        for columns in VECTOR_GROUPS[name]:
            if set(columns).issubset(header_set):
                return list(columns)
    for alias in SCALAR_ALIASES.get(name, (name,)):
        if alias in header_set:
            return [alias]
    prefix_matches = [column for column in header if column.startswith(name + "_")]
    return [prefix_matches[0]] if len(prefix_matches) == 1 else None


def _infer_fields(header: list[str], draft_rubric: dict | None = None) -> dict[str, dict]:
    if draft_rubric:
        fields = {}
        for name in _wanted_fields_from_rubric(draft_rubric):
            columns = _columns_for_field(name, header)
            if columns:
                fields[name] = {
                    "columns": columns,
                    "kind": "vector" if len(columns) == 3 else "scalar",
                    "normalizer": None,
                    "source": "draft_rubric",
                }
        if fields:
            return fields
    remaining = set(header) - COORDS
    fields: dict[str, dict] = {}
    for name, groups in VECTOR_GROUPS.items():
        for columns in groups:
            if set(columns).issubset(remaining):
                fields[name] = {"columns": list(columns), "kind": "vector", "normalizer": None, "source": "csv_fallback"}
                remaining -= set(columns)
                break
    for column in sorted(remaining):
        if column.startswith(("C_", "cell", "zoneID")):
            continue
        fields[column] = {"columns": [column], "kind": "scalar", "normalizer": None, "source": "csv_fallback"}
    if not fields:
        raise ValueError("Could not infer any scored field columns")
    return fields


def _release_state(readiness: dict) -> tuple[str, list[str]]:
    blockers = list(readiness.get("blockers") or [])
    if readiness.get("publish_ready") is True:
        return "released", blockers
    if readiness.get("input_complete") and readiness.get("gt_available"):
        return "review", blockers
    return "blocked", blockers


def _resolved_by_current_grader_standard(blocker: str) -> bool:
    lower = blocker.lower()
    phrases = (
        "no executable grader",
        "no approved formal grader",
        "no formal grader is present",
        "formal grader is present",
        "executable grader",
        "grader test",
        "grader tests",
        "packaged rubric",
        "proposed_grading",
        "draft rubric",
        "unapproved draft",
        "not a formal grader",
        "score thresholds",
        "thresholds are explicitly provisional",
        "pass/fail anchors",
        "reward aggregation",
        "thresholds have been approved",
        "thresholds, executable sampler/grader",
        "no score anchors",
        "no approved calibrated rubric",
        "formal approval",
    )
    return any(phrase in lower for phrase in phrases)


def _active_blockers(readiness: dict, *, metric_grader_executable: bool) -> list[str]:
    blockers = list(readiness.get("blockers") or [])
    if not metric_grader_executable:
        return blockers
    return [
        blocker
        for blocker in blockers
        if not _resolved_by_current_grader_standard(blocker)
    ]


def _copy_package(source: Path, target: Path) -> None:
    shutil.copytree(source / "public", target / "public")
    private = target / "private"
    private.mkdir(parents=True)
    for rel in ("reference",):
        if (source / rel).exists():
            shutil.copytree(source / rel, private / rel)


def discover_task_ids(source_run: str | Path) -> tuple[str, ...]:
    workers = Path(source_run) / "workers"
    return tuple(
        sorted(
            p.name
            for p in workers.iterdir()
            if (p / "agent" / "work" / "RELEASE_READINESS.json").exists()
        )
    )


def release(source_run: str | Path, destination: str | Path, task_ids=None) -> dict:
    source_run = Path(source_run)
    destination = Path(destination)
    task_ids = tuple(task_ids or discover_task_ids(source_run))
    if not task_ids:
        raise ValueError("No task ids found for tutorial grader release")
    if destination.exists():
        raise FileExistsError("Publish a new tutorial grader version; never overwrite")
    staging = destination.parent / (".tutorial-grader-build-" + uuid.uuid4().hex)
    staging.mkdir(parents=True)

    rows = []
    for task_id in task_ids:
        work = source_run / "workers" / task_id / "agent" / "work"
        package = work / "package"
        public = package / "public"
        readiness_path = work / "RELEASE_READINESS.json"
        author_path = source_run / "inputs" / "authors" / task_id / "author-result.json"
        if not public.exists() or not readiness_path.exists() or not author_path.exists():
            raise FileNotFoundError(f"Missing release-completion evidence for {task_id}")
        target = staging / task_id
        _copy_package(package, target)
        readiness = _read_json(readiness_path)
        author = _read_json(author_path)
        state, blockers = _release_state(readiness)
        try:
            obs_csv = _observation_csv(target / "public")
            draft_rubric_path = target / "public" / "rubric.json"
            draft_rubric = _read_json(draft_rubric_path) if draft_rubric_path.exists() else None
            fields = _infer_fields(_csv_header(obs_csv), draft_rubric)
            reference_csv = str(obs_csv.relative_to(target / "public"))
            weight_column = "cell_volume_m3" if "cell_volume_m3" in _csv_header(obs_csv) else "volume_m3"
            metric_grader_executable = True
        except Exception as exc:
            fields = {}
            reference_csv = None
            weight_column = None
            metric_grader_executable = False
            state = "blocked"
            blockers = blockers + [f"Formal metric grader unavailable: {exc}"]
        blockers = _active_blockers(readiness, metric_grader_executable=metric_grader_executable) + [
            blocker for blocker in blockers if blocker.startswith("Formal metric grader unavailable:")
        ]
        policy = {
            "version": VERSION,
            "task_id": task_id,
            "release_status": state,
            "scientific_release_status": state,
            "metric_grader_executable": metric_grader_executable,
            "scope": "score_candidate_sampled_fields_against_public_dense_observations",
            "reference_csv": reference_csv,
            "candidate_csv_contract": "CSV with the same row order and all scored field columns",
            "weight_column": weight_column,
            "fields": fields,
            "full_credit": FULL_CREDIT,
            "zero_credit": ZERO_CREDIT,
            "aggregation": "minimum_over_metrics_and_fields",
            "interpolation": "linear_between_anchors",
            "provenance_gate": "release_status must be released before leaderboard use",
            "blockers": blockers,
            "warnings": readiness.get("warnings") or [],
            "author_status": author.get("status"),
            "author_observed_endpoint": author.get("observed_endpoint"),
        }
        write_once(target / "private" / "grading.json", policy)
        write_once(target / "private" / "author-result.json", author)
        write_once(target / "private" / "release-readiness.json", readiness)
        review = review_record(task_id, readiness, author, policy)
        write_once(target / "private" / "grader-review.json", review)
        write_once(target / "task.json", {
            "task_id": task_id,
            "track": "tutorial-dense-observation",
            "version": destination.name,
            "release_status": state,
            "grader": VERSION,
            "public_identity": digest(_inventory(target / "public")),
            "policy_identity": digest(policy),
        })
        rows.append({
            "task_id": task_id,
            "release_status": state,
            "scored_fields": sorted(fields),
            "blocker_count": len(blockers),
            "metric_grader_executable": metric_grader_executable,
            "public_observation_csv": str(obs_csv.relative_to(target)) if metric_grader_executable else None,
            "review_decision": review["decision"],
        })
    manifest = {
        "release": destination.name,
        "source_run": str(source_run),
        "grader_version": VERSION,
        "task_count": len(rows),
        "released_count": sum(1 for row in rows if row["release_status"] == "released"),
        "review_count": sum(1 for row in rows if row["release_status"] == "review"),
        "blocked_count": sum(1 for row in rows if row["release_status"] == "blocked"),
        "metric_grader_executable_count": sum(1 for row in rows if row["metric_grader_executable"]),
        "review_decisions": {
            decision: sum(1 for row in rows if row["review_decision"] == decision)
            for decision in sorted({row["review_decision"] for row in rows})
        },
        "tasks": rows,
        "note": "Metric grader is executable; review/blocked tasks are not valid leaderboard releases until blockers are resolved.",
    }
    write_once(staging / "MANIFEST.json", manifest)
    (staging / "README.md").write_text(_readme(manifest), encoding="utf-8")
    staging.rename(destination)
    return manifest


def _inventory(root: Path) -> dict[str, str]:
    import hashlib

    result = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _readme(manifest: dict) -> str:
    lines = [
        "# Tutorial dense-observation grader release",
        "",
        "This release contains executable metric-grader policies generated from completed authoring evidence.",
        "A task with `release_status: review` or `blocked` must not be used as a clean leaderboard item.",
        "",
        "| task | status | metric grader executable | scored fields | blockers |",
        "|---|---:|---:|---|---:|",
    ]
    for row in manifest["tasks"]:
        fields = ", ".join(row["scored_fields"]) if row["scored_fields"] else "—"
        executable = "yes" if row["metric_grader_executable"] else "no"
        lines.append(f"| {row['task_id']} | {row['release_status']} | {executable} | {fields} | {row['blocker_count']} |")
    lines.append("")
    lines.append("Scoring anchors: normalized RMSE ≤ 5% and normalized max error ≤ 20% get full credit; normalized RMSE ≥ 30% or max error ≥ 100% get zero credit; intermediate scores are linear and aggregated by the worst field/metric.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--task-id", action="append", dest="task_ids")
    args = parser.parse_args()
    print(json.dumps(release(args.source_run, args.destination, tuple(args.task_ids) if args.task_ids else None), ensure_ascii=False, indent=2))
