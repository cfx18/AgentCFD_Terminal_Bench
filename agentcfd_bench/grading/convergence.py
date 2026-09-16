"""Explicit convergence checks; no threshold invented from a model's result."""

import math


def check(observed, rules):
    result = {}
    for rule in rules:
        value = observed
        for key in rule["path"]:
            value = value.get(key) if isinstance(value, dict) else None
        finite = type(value) in (int, float) and math.isfinite(value)
        passed = finite and rule.get("min", -math.inf) <= value <= rule.get(
            "max", math.inf
        )
        result[rule["name"]] = {
            "status": "evaluated" if finite else "not_evaluated",
            "passed": passed,
            "value": value,
            "rule": rule,
        }
    return result
