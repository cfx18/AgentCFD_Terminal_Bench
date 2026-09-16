"""Analytic polyhedral fixtures: no reference cell order or patch names."""

import itertools
import copy
import numpy as np
import pytest

from agentcfd_bench.grading.geometry import Mesh
from agentcfd_bench.grading.observations import snapshot, physical_bins, VERSION
from agentcfd_bench.grading.physics import (
    free_mesh_shock as shock,
    free_mesh_buoyant as buoyant,
    free_mesh_thermal as thermal,
)
from agentcfd_bench.grading.physics.accepted_reference import POLICY
from agentcfd_bench.grading.evaluate import evaluate
from agentcfd_bench.grading.service import active_regions, export_commands


def tetra_cube(bounds, reverse=False):
    """Six tets with an oblique body diagonal. Internal faces are connected."""
    bits = list(itertools.product((0, 1), repeat=3))
    ids = {b: i for i, b in enumerate(bits)}
    points = np.array([[bounds[j][b[j]] for j in range(3)] for b in bits], dtype=float)
    cells = []
    for order in itertools.permutations(range(3)):
        v = [0, 0, 0]
        cell = [ids[tuple(v)]]
        for axis in order:
            v[axis] = 1
            cell.append(ids[tuple(v)])
        cells.append(cell)
    if reverse:
        cells.reverse()
    centre = np.array([points[c].mean(axis=0) for c in cells])
    vol = []
    faces = {}
    for i, c in enumerate(cells):
        tet = points[c]
        vol.append(abs(np.linalg.det((tet[1:] - tet[0]).T)) / 6)
        for local in itertools.combinations(c, 3):
            f = list(local)
            a, b, d = points[f]
            if np.dot(np.cross(b - a, d - a), centre[i] - a) > 0:
                f.reverse()
            key = tuple(sorted(f))
            if key in faces:
                faces[key][2] = i
            else:
                faces[key] = [f, i, None]
    ordered = sorted(faces.values(), key=lambda row: row[2] is None)
    nf = sum(r[2] is not None for r in ordered)
    patches = {
        f"unrelated_{i}": {"start": i, "count": 1, "type": "wall"}
        for i in range(nf, len(ordered))
    }
    return Mesh(
        points,
        [r[0] for r in ordered],
        [r[1] for r in ordered],
        [r[2] for r in ordered[:nf]],
        patches,
        centre,
        vol,
    )


def foam_header(name, cls, location):
    return f'FoamFile {{version 2.0; format ascii; class {cls}; object {name}; location "{location}";}}\n'


def array_text(values):
    def entry(x):
        return (
            "(" + " ".join(f"{v:.16g}" for v in x) + ")"
            if isinstance(x, (list, np.ndarray))
            else f"{x:.16g}"
        )

    return str(len(values)) + "\n(\n" + "\n".join(entry(x) for x in values) + "\n)"


def artifacts_for(mesh, end, dimensions, fields, region="", heat=False):
    result = {}
    prefix = "mesh/" + (region + "/" if region else "")
    for name, cls, rows in [
        ("points", "vectorField", mesh.points),
        ("owner", "labelList", mesh.owner),
        ("neighbour", "labelList", mesh.neighbour),
    ]:
        result[prefix + name] = foam_header(
            name, cls, "constant/" + (region + "/" if region else "") + "polyMesh"
        ) + array_text(rows)
    result[prefix + "faces"] = (
        foam_header("faces", "faceList", "constant/polyMesh")
        + str(len(mesh.faces))
        + "\n(\n"
        + "\n".join(str(len(f)) + "(" + " ".join(map(str, f)) + ")" for f in mesh.faces)
        + "\n)"
    )
    result[prefix + "boundary"] = (
        foam_header("boundary", "polyBoundaryMesh", "constant/polyMesh")
        + str(len(mesh.boundary))
        + "\n(\n"
        + "".join(
            f'{name} {{type wall; nFaces {p["count"]}; startFace {p["start"]};}}\n'
            for name, p in mesh.boundary.items()
        )
        + ")"
    )
    values = {"C": mesh.centres, "V": mesh.volumes, **fields}
    if heat:
        values["wallHeatFlux"] = np.zeros(len(mesh.volumes))
        dimensions = {**dimensions, "wallHeatFlux": "[1 0 -3 0 0 0 0]"}
    loc = str(end) + (("/" + region) if region else "")
    for name, values in values.items():
        values = np.asarray(values)
        vector = values.ndim == 2
        cls = "volVectorField" if vector else "volScalarField"
        kind = "vector" if vector else "scalar"
        text = (
            foam_header(name, cls, loc)
            + f"dimensions {dimensions[name]};\ninternalField nonuniform List<{kind}> "
            + array_text(values)
            + ";\nboundaryField {\n"
        )
        for patch, p in mesh.boundary.items():
            value = "(0 0 0)" if vector else "0"
            if name == "wallHeatFlux":
                face = p["start"]
                value = (
                    "1"
                    if mesh.on_plane(face, 0, 0.076)
                    else "-1" if mesh.on_plane(face, 0, 0) else "0"
                )
            text += f"{patch} {{type calculated; value uniform {value};}}\n"
        result[loc + "/" + name] = text + "}\n"
    return result


@pytest.mark.parametrize("reverse", [False, True])
def test_shock_accepts_oblique_tets_and_reordered_cells(reverse):
    mesh = tetra_cube(((-5, 5), (-1, 1), (-1, 1)), reverse)
    n = len(mesh.volumes)
    fields = {
        "U": np.tile([7, 0, 0], (n, 1)),
        "T": np.full(n, 300),
        "p": np.full(n, 100000),
        "rho": np.full(n, 1.0),
    }
    a = artifacts_for(mesh, 0.007, shock.DIMENSIONS, fields, region="not_default")
    a["solver.log"] = "Time = 0.007\nEnd\n"
    observed = snapshot(a, "s-205")
    for name, value in [("Ux", 7), ("T", 300), ("p", 100000), ("rho", 1)]:
        assert observed["measurements"][name + "_axial_bin_mean"][
            "value"
        ] == pytest.approx([value] * 40)
    assert observed["measurements"]["volume"]["value"] == pytest.approx(40)


def test_cavity_split_random_patches_identified_by_geometry():
    mesh = tetra_cube(buoyant.BOUNDS)
    n = len(mesh.volumes)
    fields = {
        name: np.full(n, 0.1) for name in buoyant.DIMENSIONS if name not in ("C", "V")
    }
    fields.update(U=np.zeros((n, 3)), T=np.full(n, 293.0), p=np.full(n, 100000.0))
    a = artifacts_for(
        mesh, 42, buoyant.DIMENSIONS, fields, region="fluid_custom", heat=True
    )
    a["solver.log"] = "Time = 42\nEnd\n"
    observed = snapshot(a, "s-204")
    assert observed["heat"]["hot"] == pytest.approx(2.18 * 0.52)
    assert observed["heat"]["cold"] == pytest.approx(-2.18 * 0.52)
    for axis in ("x", "y"):
        assert observed["measurements"]["T_" + axis + "_bin_mean"][
            "value"
        ] == pytest.approx([293] * 20)
    target = {
        "task_id": "s-204",
        "reference_status": "accepted_by_expert",
        "policy": POLICY,
        "observation_version": VERSION,
        "observations": observed,
    }
    assert evaluate("s-204", a, target, native_success=True)["verdict"] == "pass"
    broken = dict(a)
    broken.pop("42/fluid_custom/wallHeatFlux")
    assert evaluate("s-204", broken, target, native_success=True)["verdict"] == "fail"


@pytest.mark.parametrize("task_id", ["s-202", "s-203"])
def test_thermal_logical_regions_can_be_renamed_and_split(task_id):
    a = {}
    end = 100 if task_id == "s-202" else 1.5
    dimensions = dict(thermal.DIMENSIONS)
    if task_id == "s-203":
        dimensions["p"] = "[0 2 -2 0 0 0 0]"
    index = 0
    for role, bins in physical_bins(task_id).items():
        for boxes in bins.values():
            for box in boxes:
                mesh = tetra_cube(box)
                n = len(mesh.volumes)
                fields = {
                    name: np.full(n, 0.1)
                    for name in dimensions
                    if name not in ("C", "V")
                }
                fields.update(
                    T=np.full(n, 301.0),
                    U=np.tile([2.0, 0, 0], (n, 1)),
                    p=np.full(n, 100000.0),
                )
                a.update(
                    artifacts_for(
                        mesh, end, dimensions, fields, region=f"piece_{index}"
                    )
                )
                index += 1
    a["solver.log"] = f"Time = {end}\nEnd\n"
    observed = snapshot(a, task_id)
    for role, bins in observed["spatial_volumes"].items():
        for row in bins.values():
            assert row["T"] == pytest.approx(301)
            if "U" in row:
                assert row["U"] == pytest.approx([2, 0, 0])
        assert sum(row["volume"] for row in bins.values()) == pytest.approx(
            thermal.VOLUMES[role]
        )


def test_export_discovery_ignores_unused_construction_mesh(tmp_path):
    for name in (
        "0/T",
        "100/a/T",
        "100/z/T",
        "constant/polyMesh/points",
        "constant/a/polyMesh/points",
    ):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture")
    assert active_regions(tmp_path) == ["a", "z"]
    commands = export_commands(
        "s-202", "chtMultiRegionFoam", ["a", "z"], geometry_v2=True
    )
    assert all("bottomWater" not in argv for _, argv in commands)
    assert all(
        argv[0] not in ("chtMultiRegionFoam", "rhoCentralFoam")
        or "-postProcess" in argv
        for _, argv in commands
    )
