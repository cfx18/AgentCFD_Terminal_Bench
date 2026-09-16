import csv
import shutil
from pathlib import Path

import pytest

from agentcfd_bench.grading.tutorial_metric import VERSION, score_csv
from agentcfd_bench.tasks.release_tutorial_graders import release


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = ROOT / "runs/tutorial-release-completion/20260916T191015Z-sol-high-codex-experiment-c6-v1"


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def policy():
    return {
        "version": VERSION,
        "weight_column": "volume_m3",
        "fields": {
            "U": {"columns": ["Ux", "Uy", "Uz"], "kind": "vector", "normalizer": 10},
            "T": {"columns": ["T"], "kind": "scalar", "normalizer": 100},
        },
        "full_credit": {"normalized_rmse": 0.05, "normalized_maximum_error": 0.20},
        "zero_credit": {"normalized_rmse": 0.30, "normalized_maximum_error": 1.0},
    }


def test_tutorial_metric_grader_scores_exact_and_bad_samples(tmp_path):
    reference = tmp_path / "reference.csv"
    exact = tmp_path / "exact.csv"
    bad = tmp_path / "bad.csv"
    rows = [
        {"x_m": 0, "y_m": 0, "z_m": 0, "volume_m3": 1, "Ux": 1, "Uy": 0, "Uz": 0, "T": 300},
        {"x_m": 1, "y_m": 0, "z_m": 0, "volume_m3": 1, "Ux": 2, "Uy": 0, "Uz": 0, "T": 320},
    ]
    write_csv(reference, rows)
    write_csv(exact, rows)
    write_csv(bad, [
        {**rows[0], "Ux": 11, "T": 400},
        {**rows[1], "Ux": 12, "T": 420},
    ])
    assert score_csv(reference, exact, policy())["reward"] == 1
    result = score_csv(reference, bad, policy())
    assert result["reward"] == 0
    assert result["field_scores"]["U"]["normalized_maximum_error"] == pytest.approx(1)


def test_tutorial_metric_grader_rejects_missing_candidate_columns(tmp_path):
    reference = tmp_path / "reference.csv"
    candidate = tmp_path / "candidate.csv"
    write_csv(reference, [{"x_m": 0, "y_m": 0, "z_m": 0, "volume_m3": 1, "Ux": 1, "Uy": 0, "Uz": 0, "T": 300}])
    write_csv(candidate, [{"x_m": 0, "y_m": 0, "z_m": 0, "volume_m3": 1, "Ux": 1, "Uy": 0, "T": 300}])
    with pytest.raises(ValueError, match="missing required field column"):
        score_csv(reference, candidate, policy())


def test_tutorial_release_builds_review_gated_packages(tmp_path):
    destination = tmp_path / "tutorial-grader-v1"
    manifest = release(SOURCE_RUN, destination, task_ids=("q-0051", "q-0176", "q-0505"))
    assert manifest["task_count"] == 3
    assert manifest["review_count"] == 3
    for task_id in ("q-0051", "q-0176", "q-0505"):
        assert (destination / task_id / "public" / "instruction.md").exists()
        assert (destination / task_id / "private" / "grading.json").exists()
        assert (destination / task_id / "private" / "grader-review.json").exists()
        assert (destination / task_id / "task.json").exists()
    assert "T" in (destination / "q-0051" / "private" / "grading.json").read_text()
    assert "Urel" in (destination / "q-0176" / "private" / "grading.json").read_text()
    q0505 = (destination / "q-0505" / "private" / "grading.json").read_text()
    assert "Cd_1" not in q0505 and "LAD_per_m" not in q0505
