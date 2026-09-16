"""Native evidence -> independently extracted quantities -> frozen GT.

No configuration-template matching, report-JSON requirement, or LLM judge.
Existing accepted finite references do not establish continuum convergence.
"""

import math
from .physics.accepted_reference import snapshot, compare, diagnostics, POLICY
from .physics import free_mesh_buoyant as buoyant, free_mesh_shock as shock
from .physics.evaluation import NativeOutputError
from .convergence import check
from . import observations
from .geometry import UnsupportedGeometry
from .physics.foam.normalize import ParserResourceLimit


def realizability(task_id, observed):
    if task_id in ("s-202", "s-203"):
        return True  # thermal extraction validates geometry, dimensions and signs
    data = observed["data"]
    values = observed["measurements"]
    if task_id == "s-204":
        heat = observed["heat"]
        scale = max(abs(heat["hot"]), abs(heat["cold"]), 1e-12)
        return (
            all(v > 0 for n in ("T", "p", "omega") for v in data[n])
            and all(v >= 0 for n in ("k", "nut", "alphat") for v in data[n])
            and min(data["T"]) >= 288.15 - 1e-3
            and max(data["T"]) <= 307.75 + 1e-3
            and abs(values["volume"]["value"] - buoyant.VOLUME) < 1e-8
            and abs(
                values["mass"]["value"]
                / (100000 / (shock.GAS_R * 293) * buoyant.VOLUME)
                - 1
            )
            <= 1e-4
            and heat["hot"] > 0
            and heat["cold"] < 0
            and max(abs(heat[n]) for n in ("frontAndBack", "topAndBottom")) / scale
            <= 1e-5
        )
    exact = shock.solution()
    return (
        abs(values["volume"]["value"] - 40) < 1e-6
        and all(v > 0 for n in ("p", "rho", "T") for v in data[n])
        and values["transverse_velocity_rms"]["value"] <= 1e-7
        and observed["equation_of_state_relative_max"] <= 1e-4
        and abs(values["mass"]["value"] / (20 * (exact.left.rho + exact.right.rho)) - 1)
        <= 1e-4
        and abs(
            values["total_energy"]["value"]
            / (20 * (exact.left.p + exact.right.p) / (shock.GAMMA - 1))
            - 1
        )
        <= 1e-4
        and abs(
            values["axial_momentum"]["value"]
            / (shock.AREA * (exact.left.p - exact.right.p) * shock.END)
            - 1
        )
        <= 1e-4
    )


def evaluate(task_id, artifacts, target, *, native_success, convergence_rules=()):
    if not native_success:
        return {
            "verdict": "fail",
            "reason": "native_run_not_completed",
            "checks": {"native_completion": False},
        }
    if (
        target["policy"] != POLICY
        or target["reference_status"] != "accepted_by_expert"
        or target["task_id"] != task_id
    ):
        return {"verdict": "error", "reason": "reference_identity_mismatch"}
    try:
        observation_version = target.get("observation_version")
        if observation_version not in (None, observations.VERSION):
            return {"verdict": "error", "reason": "unsupported_observation_version"}
        observed = (observations.snapshot if observation_version else snapshot)(
            artifacts, task_id
        )
    except ParserResourceLimit as exc:
        return {
            "verdict": "error",
            "reason": "grader_resource_limit",
            "detail": str(exc),
            "needs_expert_review": True,
        }
    except UnsupportedGeometry as exc:
        return {
            "verdict": "error",
            "reason": "grader_mesh_representation_unsupported",
            "detail": str(exc),
            "needs_expert_review": True,
        }
    except NativeOutputError as exc:
        if any(
            term in str(exc)
            for term in (
                "Cartesian",
                "tile the supplied 1D tube",
                "cells do not cover supplied geometry",
            )
        ):
            return {
                "verdict": "error",
                "reason": "grader_mesh_representation_unsupported",
                "detail": str(exc),
                "needs_expert_review": True,
            }
        return {
            "verdict": "fail",
            "reason": "native_output_incomplete_or_invalid",
            "detail": str(exc),
        }
    except Exception as exc:
        return {
            "verdict": "error",
            "reason": "extractor_exception",
            "detail": type(exc).__name__ + ": " + str(exc),
        }
    try:
        matched, errors = compare(task_id, observed, target["observations"])
        diagnostic = (
            observed["diagnostics"]
            if observation_version
            else diagnostics(task_id, observed, artifacts)
        )
        convergence = check({**observed, **diagnostic}, convergence_rules)
        checks = {
            "native_completion": True,
            "field_realizability": realizability(task_id, observed),
            "reference_match": matched,
        }
        if convergence_rules:
            checks["convergence"] = all(row["passed"] for row in convergence.values())
        return {
            "verdict": "pass" if all(checks.values()) else "fail",
            "reason": "physical_acceptance",
            "checks": checks,
            "errors": errors,
            "measurements": observed["measurements"],
            "diagnostics": diagnostic,
            "convergence": convergence,
            "convergence_certified": bool(convergence_rules) and checks["convergence"],
            "policy": "accepted-gt-v1",
            "reference_policy": POLICY,
            "observation_version": observation_version or "legacy-v1",
        }
    except Exception as exc:
        return {
            "verdict": "error",
            "reason": "grader_exception",
            "detail": type(exc).__name__ + ": " + str(exc),
        }
