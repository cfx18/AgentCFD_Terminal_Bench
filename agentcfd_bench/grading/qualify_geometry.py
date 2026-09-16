"""Offline author qualification. No model calls and no solver time advancement.

Replays verified historical fields through the production native exporter. If
mesh topology was not archived, rebuild ONLY the original blockMesh and prove
its C/V against recorded C/V before pairing it with historical solution fields.
Outputs are append-only, separate from both historical evidence and releases.
"""

import argparse
import copy
from pathlib import Path
import shutil
import time

import numpy as np

from ..records.store import read, digest, write_once
from ..execution.runner import Runner
from ..execution.sandbox import Sandbox
from .service import artifact_text, export_native
from .observations import snapshot, VERSION
from .physics import free_mesh_shock as shock, free_mesh_buoyant as buoyant
from .physics.accepted_reference import compare
from .evaluate import evaluate

PROJECT = Path(__file__).resolve().parents[2]


def source_evidence(task_id):
    target = read(
        PROJECT / "tasks/releases/workbench-v3" / task_id / "private/reference.json"
    )
    source = Path(target["source"]["run_directory"])
    result, inputs = read(source / "result.json"), read(source / "inputs.json")
    if not (
        digest(result["payload"]) == result["hash"] == target["source"]["result_hash"]
        and digest(inputs["payload"]) == inputs["hash"] == target["input_hash"]
        and digest(result["payload"]["artifacts"]) == target["source"]["artifact_hash"]
    ):
        raise ValueError("Historical reference evidence integrity mismatch")
    return target, inputs["payload"], result["payload"]["artifacts"]


def wait(runner, operation):
    while True:
        result = runner.status(operation["run_id"])
        if result["lifecycle"] != "running":
            break
        time.sleep(0.1)
    if result["lifecycle"] != "completed" or not result["success"]:
        raise RuntimeError(
            str(result) + " " + str(runner.logs(operation["run_id"], stream="stderr"))
        )
    return runner.verify(operation["run_id"])[0]


def prepare_case(task_id, root, sandbox):
    target, inputs, artifacts = source_evidence(task_id)
    work = root / "work"
    if (root / "prepared.json").exists():
        return target, artifacts, work
    work.mkdir(parents=True, exist_ok=True)
    # A prior unfinished prepare must be inspected, not replayed unknowingly.
    if (root / "prepare-intent.json").exists():
        raise RuntimeError("Preparation outcome unknown; inspect native receipts")
    write_once(
        root / "prepare-intent.json", {"task": task_id, "source": target["source"]}
    )
    for name, text in inputs.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    has_mesh = any(p.startswith("mesh/") and p.endswith("/points") for p in artifacts)
    if not has_mesh:
        runner = Runner(root / "mesh-only-runs", sandbox, seconds=60)
        operation = runner.start(work, ["blockMesh"], kind="exec")
        native = wait(runner, operation)
        shutil.copytree(native / "artifacts", work, dirs_exist_ok=True)
    for name, text in artifacts.items():
        if name.startswith("mesh/"):
            pieces = name.split("/")
            name = "/".join(["constant", *pieces[1:-1], "polyMesh", pieces[-1]])
        elif name.endswith(".log"):
            continue
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    write_once(
        root / "prepared.json",
        {
            "rebuilt_block_mesh_only": not has_mesh,
            "source_artifacts": digest(artifacts),
        },
    )
    return target, artifacts, work


def qualify(task_id, root):
    root = Path(root) / task_id
    root.mkdir(parents=True, exist_ok=True)
    if (root / "qualification.json").exists():
        return read(root / "qualification.json")
    sandbox = Sandbox(
        foam_root=str(PROJECT / "environments/native-v2306/foam"), mpi="intelmpi"
    )
    target, original, work = prepare_case(task_id, root, sandbox)
    program = {
        "s-202": "chtMultiRegionFoam",
        "s-203": "pimpleFoam",
        "s-204": "buoyantSimpleFoam",
        "s-205": "rhoCentralFoam",
    }[task_id]
    artifacts, seconds = export_native(
        work,
        task_id,
        program,
        root / "export",
        sandbox,
        original["solver.log"],
        geometry_v2=True,
    )
    if task_id in ("s-204", "s-205"):
        end = 6000 if task_id == "s-204" else 0.007
        dimensions = buoyant.DIMENSIONS if task_id == "s-204" else shock.DIMENSIONS
        old = shock.native_fields(
            original, end, {"C": dimensions["C"], "V": dimensions["V"]}
        )
        new = shock.native_fields(
            artifacts, end, {"C": dimensions["C"], "V": dimensions["V"]}
        )
        for name in ("C", "V"):
            if not np.allclose(old[name], new[name], rtol=2e-6, atol=1e-12):
                raise ValueError(
                    "Rebuilt mesh does not match historical native " + name
                )
    observed = snapshot(artifacts, task_id)
    updated = copy.deepcopy(target)
    updated["observation_version"] = VERSION
    updated["observations"] = {
        key: observed[key]
        for key in ("measurements", "spatial_volumes")
        if key in observed
    }
    updated["observation_provenance"] = {
        "original_reference_identity": digest(target),
        "original_field_artifacts": digest(original),
        "new_native_artifacts": digest(artifacts),
        "solver_rerun": False,
        "reason": "true_polyhedral_overlap_and_geometric_boundary_identification",
    }
    score = evaluate(task_id, artifacts, updated, native_success=True)
    if score["verdict"] != "pass":
        raise ValueError("Reference replay did not pass: " + str(score))
    _, change = compare(task_id, observed, target["observations"])
    # Deliberately wrong evidence must fail even with a successful native exit.
    bad = copy.deepcopy(updated["observations"])
    if task_id in ("s-202", "s-203"):
        for bins in bad["spatial_volumes"].values():
            for row in bins.values():
                row["T"] += 100
    else:
        key = "T_x_bin_mean" if task_id == "s-204" else "p_axial_bin_mean"
        bad["measurements"][key]["value"] = [
            v + 1e6 for v in bad["measurements"][key]["value"]
        ]
    if compare(task_id, bad, updated["observations"])[0]:
        raise ValueError("Corrupt field sentinel passed")
    write_once(root / "artifacts.json", artifacts)
    write_once(root / "reference.json", updated)
    write_once(root / "score.json", score)
    result = {
        "task_id": task_id,
        "reference_replay": "pass",
        "corrupt_field_rejected": True,
        "observation_version": VERSION,
        "reference_identity": digest(updated),
        "old_vs_new": change,
        "native_export_seconds": seconds,
        "solver_rerun": False,
    }
    write_once(root / "qualification.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--tasks", nargs="+", default=["s-202", "s-203", "s-204", "s-205"]
    )
    args = parser.parse_args()
    for task in args.tasks:
        print(task + " start", flush=True)
        result = qualify(task, args.output)
        print(
            task
            + " "
            + result["reference_replay"]
            + " export seconds="
            + str(result["native_export_seconds"]),
            flush=True,
        )


if __name__ == "__main__":
    main()
