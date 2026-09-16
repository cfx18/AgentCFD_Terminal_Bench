"""Large native fields are not macro bombs; extractor limits are not failures."""

import importlib
from pathlib import Path

import pytest

from agentcfd_bench.grading.physics.evaluation import native_output_reader
from agentcfd_bench.grading.physics.foam.normalize import (
    ParserResourceLimit,
    UnsupportedInput,
)
from agentcfd_bench.grading.physics.foam.parsed import Dictionary, read, resolve
from agentcfd_bench.grading.physics.foam.science_metrics import field_values
from agentcfd_bench.tasks.loader import Task

PROJECT = Path(__file__).resolve().parents[1]


def vector_field(count, body=None):
    body = "(1 2 3)\n" * count if body is None else body
    return (
        'FoamFile {format ascii; class volVectorField; object U; location "2700";}\n'
        'dimensions [0 1 -1 0 0 0 0];\n'
        f'internalField nonuniform List<vector> {count} (\n{body});\n'
        'boundaryField {wall {type fixedValue; value uniform (0 0 0);}}\n'
    )


def test_actual_incident_size_vector_field_is_accepted():
    values = field_values(vector_field(100800), "U", 100800,
                          "[0 1 -1 0 0 0 0]", 2700)
    assert len(values) == 100800
    assert values[0] == values[-1] == [1.0, 2.0, 3.0]


@pytest.mark.parametrize("components", [1, 3])
def test_literal_at_supported_million_cell_limit_is_not_macro_expansion(components):
    row = ("1",) if components == 1 else ("(", "1", "2", "3", ")")
    literal = row * 1000000
    # No extra expanded copy, and no new higher arbitrary token threshold.
    assert resolve(Dictionary((("values", literal),)))["values"] is literal


@pytest.mark.parametrize("body", ["(1 2 3)\n", "(1 2)\n(3 4)\n", "(nan 2 3)\n(1 2 3)\n"])
def test_count_shape_and_nonfinite_values_still_fail(body):
    with pytest.raises(ValueError):
        field_values(vector_field(2, body), "U", 2, "[0 1 -1 0 0 0 0]", 2700)


def test_macro_expansion_limit_and_cycle_protection_remain():
    large = ("1",) * 250001
    tree = Dictionary((("source", large), ("expanded", ("$source", "$source"))))
    with pytest.raises(ParserResourceLimit, match="Expanded value"):
        resolve(tree)
    with pytest.raises(UnsupportedInput, match="Cyclic"):
        read("a $b; b $a;")
    assert read("a 1; b $a;")["b"] == ("1",)


def test_resource_limit_survives_native_reader_and_is_not_model_failure(monkeypatch):
    module = importlib.import_module("agentcfd_bench.grading.evaluate")
    task = Task.load(PROJECT / "tasks/releases/workbench-v3-polyhedral-v2/s-204")
    target, _ = task.private()

    @native_output_reader
    def exhausted(*args):
        raise ParserResourceLimit("Expanded value exceeds safety limit")

    monkeypatch.setattr(module.observations, "snapshot", exhausted)
    result = module.evaluate("s-204", {}, target, native_success=True)
    assert result["verdict"] == "error"
    assert result["reason"] == "grader_resource_limit"
    assert result["needs_expert_review"] is True


def test_dictionary_depth_limit_is_typed_resource_error():
    with pytest.raises(ParserResourceLimit, match="nesting"):
        read("a {" * 66 + "x 1;" + "}" * 66)
