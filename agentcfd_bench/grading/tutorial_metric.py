"""Deterministic metric grader for tutorial dense-observation releases.

This module scores a candidate sampled-field CSV against a frozen reference CSV.
It deliberately does not decide whether the reference is scientifically approved:
that provenance/release decision is recorded separately in the task's
``private/grading.json``.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable


VERSION = "tutorial-dense-metric-grader-v1"

FULL_CREDIT = {"normalized_rmse": 0.05, "normalized_maximum_error": 0.20}
ZERO_CREDIT = {"normalized_rmse": 0.30, "normalized_maximum_error": 1.00}

COORDINATE_COLUMNS = {
    "cell_id",
    "x_m",
    "y_m",
    "z_m",
    "volume_m3",
    "cell_volume_m3",
    "volume",
}


def _read_csv(path: str | Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        for line_number, row in enumerate(reader, start=2):
            parsed = {}
            for key, value in row.items():
                if value is None or value == "":
                    raise ValueError(f"Missing value in {path}:{line_number}:{key}")
                try:
                    number = float(value)
                except ValueError as exc:
                    raise ValueError(
                        f"Non-numeric value in {path}:{line_number}:{key}: {value!r}"
                    ) from exc
                if not math.isfinite(number):
                    raise ValueError(f"Non-finite value in {path}:{line_number}:{key}")
                parsed[key] = number
            rows.append(parsed)
    if not rows:
        raise ValueError(f"CSV has no data rows: {path}")
    return rows


def _weight_column(columns: Iterable[str]) -> str:
    cols = set(columns)
    if "volume_m3" in cols:
        return "volume_m3"
    if "cell_volume_m3" in cols:
        return "cell_volume_m3"
    raise ValueError("Reference CSV must include volume_m3 or cell_volume_m3")


def _components_from_policy(policy: dict) -> dict[str, list[str]]:
    fields = policy.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("Grading policy must define non-empty fields")
    result = {}
    for name, spec in fields.items():
        columns = spec.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ValueError(f"Field {name!r} must define columns")
        result[name] = [str(c) for c in columns]
    return result


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    total = sum(weights)
    if total <= 0 or not math.isfinite(total):
        raise ValueError("Weights must sum to a positive finite value")
    return sum(v * w for v, w in zip(values, weights)) / total


def _normalizer(rows: list[dict[str, float]], columns: list[str], explicit: float | None) -> float:
    if explicit is not None:
        value = float(explicit)
        if value > 0 and math.isfinite(value):
            return value
        raise ValueError(f"Invalid explicit normalizer: {explicit!r}")
    if len(columns) == 1:
        values = [r[columns[0]] for r in rows]
        span = max(values) - min(values)
        if span > 0 and math.isfinite(span):
            return span
        rms = math.sqrt(sum(v * v for v in values) / len(values))
        return rms if rms > 0 and math.isfinite(rms) else 1.0
    magnitudes = [
        math.sqrt(sum(r[column] * r[column] for column in columns))
        for r in rows
    ]
    span = max(magnitudes) - min(magnitudes)
    if span > 0 and math.isfinite(span):
        return span
    rms = math.sqrt(sum(v * v for v in magnitudes) / len(magnitudes))
    return rms if rms > 0 and math.isfinite(rms) else 1.0


def _component_score(error: float, good: float, bad: float) -> float:
    if not all(math.isfinite(v) for v in (error, good, bad)) or not 0 <= good < bad:
        raise ValueError("Invalid error or reward anchors")
    if error <= good:
        return 1.0
    if error >= bad:
        return 0.0
    return (bad - error) / (bad - good)


def score_csv(reference_csv: str | Path, candidate_csv: str | Path, policy: dict) -> dict:
    """Score a candidate sampled CSV against a reference sampled CSV.

    Candidate rows must align one-to-one with the reference rows. The grader is
    intentionally strict: missing, extra, non-finite, or unannounced fields are
    infrastructure/evidence errors, not silently dropped samples.
    """

    if policy.get("version") != VERSION:
        raise ValueError("Unsupported tutorial metric grader policy")
    reference = _read_csv(reference_csv)
    candidate = _read_csv(candidate_csv)
    if len(reference) != len(candidate):
        raise ValueError(
            f"Candidate row count {len(candidate)} does not match reference {len(reference)}"
        )
    fields = _components_from_policy(policy)
    weight_key = policy.get("weight_column") or _weight_column(reference[0])
    weights = [r[weight_key] for r in reference]
    if any(w <= 0 or not math.isfinite(w) for w in weights):
        raise ValueError("Reference weights must be positive and finite")

    field_scores = {}
    for field, columns in fields.items():
        for column in columns:
            if column not in reference[0]:
                raise ValueError(f"Reference missing required field column {column!r}")
            if column not in candidate[0]:
                raise ValueError(f"Candidate missing required field column {column!r}")
        row_errors = []
        for rrow, crow in zip(reference, candidate):
            squared = [(crow[column] - rrow[column]) ** 2 for column in columns]
            row_errors.append(math.sqrt(sum(squared)))
        rmse = math.sqrt(_weighted_mean([v * v for v in row_errors], weights))
        maximum = max(row_errors)
        spec = policy["fields"][field]
        normalizer = _normalizer(reference, columns, spec.get("normalizer"))
        normalized_rmse = rmse / normalizer
        normalized_maximum = maximum / normalizer
        components = {
            "normalized_rmse": _component_score(
                normalized_rmse,
                policy["full_credit"]["normalized_rmse"],
                policy["zero_credit"]["normalized_rmse"],
            ),
            "normalized_maximum_error": _component_score(
                normalized_maximum,
                policy["full_credit"]["normalized_maximum_error"],
                policy["zero_credit"]["normalized_maximum_error"],
            ),
        }
        field_scores[field] = {
            "columns": columns,
            "normalizer": normalizer,
            "rmse": rmse,
            "maximum_error": maximum,
            "normalized_rmse": normalized_rmse,
            "normalized_maximum_error": normalized_maximum,
            "components": components,
            "reward": min(components.values()),
        }

    reward = min(row["reward"] for row in field_scores.values())
    return {
        "grading_schema_version": "tutorial-dense-result-v1",
        "grader_version": VERSION,
        "metric_status": "completed",
        "coverage": 1.0,
        "rows": len(reference),
        "field_scores": field_scores,
        "reward": reward,
        "verdict": "pass" if reward == 1.0 else "fail",
        "reason": (
            "tutorial_dense_full_credit"
            if reward == 1.0
            else "tutorial_dense_below_full_credit"
        ),
    }
