"""Publish a new observation release only after native replay and tests pass.

This does not run models, alter old releases, change tolerances or solve GT cases.
"""

import argparse
import hashlib
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from ..records.store import read, write_once, digest
from .observations import VERSION
from .qualification import grader_identity

PROJECT = Path(__file__).resolve().parents[2]
TASKS = ("s-202", "s-203", "s-204", "s-205")

COMMON = """# Independently extracted observations

Keep your actual native mesh and solution fields. The evaluator reads the frozen
solver output, independently exports cell geometry, and compares physical
observations with a hidden, expert-accepted finite numerical reference. No
self-reported JSON is required. A successful OpenFOAM exit alone is not a pass.

You choose cell types, grading, resolution, cell ordering, region names and patch
names. Observation regions and wall names below identify physical locations, not
required OpenFOAM identifiers. Statistics use volume or face-area weights. Cells
crossing an observation boundary contribute by their actual geometric overlap;
each stored cell value is treated as piecewise constant within that polyhedron.
Binary native output is supported. Preserve the field names and physical units
of the quantities being observed; the evaluator generates C/V itself.

Residuals, saved-iterate changes and heat balance are recorded where available.
Missing diagnostic evidence is not zero. Agreement with this finite reference
does not certify mesh independence or strict steady-state convergence. Report
remaining numerical uncertainty honestly.
"""

DETAILS = {
    "s-202": """At physical time 100 s, compare T in each of the five supplied material
volumes, and U, absolute/gauge p as specified in the question, and p_rgh in the
two fluids. Split each material into intersections with four equal x slices over
[-0.1, 0.1] m and two equal z slices over [-0.05, 0.05] m. Only nonempty physical
intersections are compared. Compute volume means in those subvolumes. Temperature
error is scaled by the reference temperature rise above 300 K, not absolute
temperature. Preserve previous writes and native fluxes for expert diagnostics.
""",
    "s-203": """At physical time 1.5 s, compare volume-averaged T, U, kinematic p, k,
epsilon and nut in fixed physical subvolumes. Split the inlet passage
0 < x < 0.2 m into five equal axial segments. Split each branch of the vertical
passage (x from 0.2 to 0.22 m), y from -0.21 to -0.01 m and from 0.01 to 0.21 m,
into five equal y segments; keep the central junction (-0.01 < y < 0.01 m) as
one subvolume. Every subvolume spans the full thickness 0 < z < 0.02 m.
Temperature differences use a 300 K reference offset. The separately reported
temperature excess above the 315 K inlet is important for diagnosing heating.
""",
    "s-204": """At the final saved iterate, compare T and vertical velocity Uy profiles
in 20 equal x bins over [0, 0.076] m and 20 equal y bins over [0, 2.18] m, each
spanning the full perpendicular cross-section. Compare area-integrated heat
rates at the hot x=0.076 m wall and cold x=0 wall. Native wallHeatFlux is positive
into the fluid; heat-flux density must be multiplied by face area.

Also check field signs, total cavity volume, conservation of the initial ideal-gas
mass, temperature bounds, hot/cold heat directions and negligible heat at the
four adiabatic walls. Preserve T, U, absolute p, p_rgh, k, omega, nut and alphat.
Save at least two iterates when feasible for a separate stationarity diagnostic;
nearby writes alone do not prove steady convergence.
""",
    "s-205": """At physical time 0.007 s, compare rho, p, T and axial velocity Ux in
40 equal x bins over [-5, 5] m, each spanning the full 2 m by 2 m cross-section.
Transverse mesh subdivision is allowed. Preserve rho, p, T and U. Also evaluate
total volume, mass, axial momentum, total energy, transverse velocity and the
ideal-gas equation of state. These checks use actual native values, not the
analytic solution substituted for the computed fields.
""",
}


def publish(audit, release, tests):
    audit, release, tests = (
        Path(audit).resolve(),
        Path(release).resolve(),
        Path(tests).resolve(),
    )
    tree = ET.parse(tests)
    cases = list(tree.iter("testcase"))
    if not cases or any(
        list(c.iter(tag)) for c in cases for tag in ("failure", "error", "skipped")
    ):
        raise ValueError(
            "All qualification tests must complete without failure/error/skip"
        )
    required = (
        "test_skew_mesh_partition_conserves_volume",
        "test_concave_polyhedron_signed_decomposition",
        "test_shock_accepts_oblique_tets_and_reordered_cells",
        "test_thermal_logical_regions_can_be_renamed_and_split",
        "test_real_alternative_cross_section_mesh_and_private_grading",
        "test_native_multiregion_export_after_region_and_patch_rename",
    )
    if not all(
        any(c.get("name", "").startswith(name) for c in cases) for name in required
    ):
        raise ValueError("Required geometry/native regression coverage missing")
    code = grader_identity()
    checks = {}
    for task_id in TASKS:
        evidence = read(audit / task_id / "qualification.json")
        target = read(audit / task_id / "reference.json")
        if (
            evidence["reference_replay"] != "pass"
            or not evidence["corrupt_field_rejected"]
            or evidence["reference_identity"] != digest(target)
        ):
            raise ValueError("Native reference replay not qualified: " + task_id)
        checks[task_id] = (evidence, target)
    release.mkdir(parents=True, exist_ok=False)
    for task_id, (evidence, target) in checks.items():
        dest = release / task_id
        dest.mkdir()
        shutil.copytree(
            PROJECT / "tasks/releases/workbench-v3" / task_id / "public",
            dest / "public",
        )
        (dest / "public/observations.md").write_text(COMMON + "\n" + DETAILS[task_id])
        write_once(
            dest / "task.json",
            {
                "schema": "openfoam-task-v3",
                "id": task_id,
                "source": "expert-output-v1",
                "observation_version": VERSION,
            },
        )
        write_once(dest / "private/reference.json", target)
        write_once(
            dest / "private/grading.json",
            {
                "policy": "accepted-gt-v1",
                "convergence_rules": [],
                "convergence_status": "diagnostic_only_until_expert_thresholds_are_registered",
                "reference_revision": "same_native_fields_polyhedral_observations_v2",
                "observation_version": VERSION,
                "general_mesh_qualified": True,
            },
        )
        write_once(
            dest / "private/qualification.json",
            {
                **evidence,
                "grader_identity": code,
                "regression_tests_passed": True,
                "test_count": len(cases),
                "test_report_sha256": hashlib.sha256(tests.read_bytes()).hexdigest(),
                "tested_meshes": [
                    "orthogonal_hex",
                    "skew_hex",
                    "tetrahedral",
                    "concave_polyhedral",
                    "transverse_subdivision",
                ],
                "tested_names": [
                    "renamed_regions",
                    "split_regions",
                    "renamed_and_split_boundary_patches",
                ],
                "limits": [
                    "At most 1000000 cells per region.",
                    "Unsupported or inconsistent extraction remains infrastructure error, never a claimed physical failure.",
                ],
            },
        )
    return release


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--tests", required=True)
    args = parser.parse_args()
    print(publish(args.audit, args.release, args.tests))
