"""Trusted output export in a separate no-GT sandbox, followed by private scoring."""

from pathlib import Path
import shutil
import time
import re

from .evaluate import evaluate
from ..execution.runner import Runner
from ..execution.files import inventory
from ..records.store import read, write_once, lock


def artifact_text(root, solver_log):
    result = {"solver.log": solver_log}
    mesh_aliases = {}
    for name in inventory(root):
        path = Path(root) / name
        try:
            text = path.read_text()
        except UnicodeError:
            continue
        result[name] = text
        parts = name.split("/")
        if (
            len(parts) >= 3
            and (parts[0] == "constant" or re.fullmatch(r"[0-9.eE+\-]+", parts[0]))
            and "polyMesh" in parts
        ):
            i = parts.index("polyMesh")
            key = "/".join(["mesh", *parts[1:i], *parts[i + 1 :]])
            stamp = float("-inf") if parts[0] == "constant" else float(parts[0])
            if key not in mesh_aliases or stamp > mesh_aliases[key][0]:
                mesh_aliases[key] = (stamp, text)
    result.update({key: value[1] for key, value in mesh_aliases.items()})
    return result


def export_commands(task_id, native_program, regions=None, *, geometry_v2=False):
    # These only export measurements; they do not select the Agent's physical model.
    regions = (
        regions
        if regions is not None
        else (
            ("bottomWater", "topAir", "heater", "leftSolid", "rightSolid")
            if task_id == "s-202"
            else ("",)
        )
    )
    commands = [
        (
            "format",
            [
                "foamDictionary",
                "system/controlDict",
                "-disableFunctionEntries",
                "-entry",
                "writePrecision",
                "-set",
                "17",
            ],
        ),
        (
            "format",
            [
                "foamDictionary",
                "system/controlDict",
                "-disableFunctionEntries",
                "-entry",
                "writeFormat",
                "-set",
                "ascii",
            ],
        ),
        (
            "format",
            [
                "foamDictionary",
                "system/controlDict",
                "-disableFunctionEntries",
                "-entry",
                "writeCompression",
                "-set",
                "off",
            ],
        ),
    ]
    for region in regions:
        flags = ["-region", region] if region else []
        commands.append(("format", ["foamFormatConvert", *flags, "-constant"]))
        for function in ("writeCellCentres", "writeCellVolumes"):
            commands.append(
                ("geometry", ["postProcess", *flags, "-func", function, "-latestTime"])
            )
        if task_id == "s-204" or (task_id == "s-202" and not geometry_v2):
            commands.append(
                (
                    "wall_heat_flux",
                    [
                        native_program,
                        "-postProcess",
                        *flags,
                        "-func",
                        "wallHeatFlux",
                        "-latestTime",
                    ],
                )
            )
        if not geometry_v2 and (
            task_id == "s-203"
            or (task_id == "s-202" and region in ("bottomWater", "topAir"))
        ):
            for field in ("U", "T"):
                commands.append(
                    (
                        "gradient",
                        [
                            "postProcess",
                            *flags,
                            "-func",
                            f"grad({field})",
                            "-latestTime",
                        ],
                    )
                )
    return commands


class ExportError(RuntimeError):
    def __init__(self, operation, outcome):
        self.operation, self.outcome = operation, outcome
        super().__init__("Native measurement export failed")


def active_regions(work):
    """Final native T identifies used meshes; ignore construction-only meshes."""
    work = Path(work)
    times = [
        p
        for p in work.iterdir()
        if p.is_dir() and re.fullmatch(r"[0-9.eE+\-]+", p.name)
    ]
    if not times:
        raise ValueError("No native field time directory")
    final = max(times, key=lambda p: float(p.name))
    result = []
    for field in [
        *final.glob("T"),
        *final.glob("T.gz"),
        *final.glob("*/T"),
        *final.glob("*/T.gz"),
    ]:
        name = "" if field.parent == final else field.parent.name
        if name not in result:
            result.append(name)
    if not result:
        raise ValueError("No final native temperature field")
    return sorted(result)


def format_projection(work, root, index, region):
    """v2306 converter opens default polyMesh even with -region.

    Supply an exact copy of the selected region mesh in an export-only view.
    Publish ONLY that region back; never inject the placeholder into the case.
    The original inputs and the projection both remain auditable.
    """
    work = Path(work)
    projection = Path(root) / f"format-view-{index:02d}"
    if projection.exists():
        raise RuntimeError("Unbound format projection requires inspection")

    def omit_default(path, names):
        base = Path(path)
        return (
            ["polyMesh"]
            if base.parent == work
            and (base.name == "constant" or re.fullmatch(r"[0-9.eE+\-]+", base.name))
            and "polyMesh" in names
            else []
        )

    shutil.copytree(work, projection, ignore=omit_default)
    for base in work.iterdir():
        if base.is_dir() and (
            base.name == "constant" or re.fullmatch(r"[0-9.eE+\-]+", base.name)
        ):
            mesh = base / region / "polyMesh"
            if mesh.is_dir():
                shutil.copytree(mesh, projection / base.name / "polyMesh")
    return projection


def publish_export(source, work, region=None):
    if region is None:
        shutil.copytree(source, work, dirs_exist_ok=True)
    else:
        for base in Path(source).iterdir():
            if base.is_dir() and (
                base.name == "constant" or re.fullmatch(r"[0-9.eE+\-]+", base.name)
            ):
                selected = base / region
                if selected.is_dir():
                    shutil.copytree(
                        selected, Path(work) / base.name / region, dirs_exist_ok=True
                    )


def export_native(
    work, task_id, native_program, root, sandbox, solver_log, *, geometry_v2=False
):
    """Same bounded, recoverable native export for submissions and author replay.

    Author replay supplies verified historical evidence, never a pretend solver
    operation. Neither path mounts private reference data into the exporter.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    exports = Runner(root / "export-runs", sandbox, seconds=300)
    selected = active_regions(work) if geometry_v2 else None
    extra = {}
    commands = export_commands(
        task_id, native_program, selected, geometry_v2=geometry_v2
    )
    for index, (label, argv) in enumerate(commands):
        projection_region = (
            argv[argv.index("-region") + 1]
            if argv[0] == "foamFormatConvert" and "-region" in argv
            else None
        )
        binding = root / f"export-{index:02d}.json"
        if binding.exists():
            operation = read(binding)
            if (
                read(exports.directory(operation["run_id"]) / "spec.json")["argv"]
                != argv
            ):
                raise RuntimeError(
                    "Export recipe changed after dispatch; do not reuse results"
                )
        else:
            intent = root / f"export-{index:02d}-intent.json"
            if intent.exists():
                raise RuntimeError("Export start outcome unknown")
            write_once(intent, {"argv": argv})
            export_work = (
                format_projection(work, root, index, projection_region)
                if projection_region
                else work
            )
            operation = exports.start(export_work, argv, kind="exec")
            write_once(binding, operation)
        while True:
            outcome = exports.status(operation["run_id"])
            if outcome["lifecycle"] != "running":
                break
            time.sleep(0.1)
        if outcome["lifecycle"] != "completed" or not outcome["success"]:
            raise ExportError(operation, outcome)
        directory, _ = exports.verify(operation["run_id"])
        publish_export(directory / "artifacts", work, projection_region)
        extra[label + ".log"] = extra.get(label + ".log", "") + (
            directory / "stdout.log"
        ).read_text(errors="replace")
    artifacts = artifact_text(work, solver_log)
    artifacts.update(extra)
    return artifacts, 300 - exports.remaining()


def grade_submission(task, runner, run_id, root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with lock(root / "grading.lock"):
        _, policy = task.private()
        if policy.get("policy") == "dense-observation-v1":
            from .dense_native import grade

            return grade(task, runner, run_id, root)
        if (root / "result.json").exists():
            return read(root / "result.json")
        native, result = runner.verify(run_id)
        if result["kind"] != "run":
            raise ValueError("Cannot grade an arbitrary preparation script")
        target, policy = task.private()
        if not result["success"]:
            value = evaluate(task.task_id, {}, target, native_success=False)
            write_once(root / "result.json", value)
            return value
        work = root / "export-work"
        if not work.exists():
            shutil.copytree(native / "artifacts", work)
        # No model, GT, secret or grading code is mounted in the export sandbox.
        spec = read(native / "spec.json")
        log = (native / "stdout.log").read_text(errors="replace")
        try:
            from .observations import VERSION

            geometry_v2 = target.get("observation_version") == VERSION
            artifacts, seconds = export_native(
                work,
                task.task_id,
                Path(spec["argv"][0]).name,
                root,
                runner.sandbox,
                log,
                geometry_v2=geometry_v2,
            )
            value = evaluate(
                task.task_id,
                artifacts,
                target,
                native_success=result["success"],
                convergence_rules=policy["convergence_rules"],
            )
            value["grader_native_seconds"] = seconds
        except ExportError as exc:
            value = {
                "verdict": "error",
                "reason": "measurement_export_failed",
                "operation": exc.operation,
                "details": exc.outcome,
            }
        except Exception as exc:
            value = {
                "verdict": "error",
                "reason": "grading_infrastructure_error",
                "detail": type(exc).__name__ + ": " + str(exc),
            }
        write_once(root / "result.json", value)
        return value
