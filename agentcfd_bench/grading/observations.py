"""Mesh-independent observations of native finite-volume fields.

Cells are piecewise constant (the native finite-volume representation). Physical
observation boxes clip actual oriented polyhedra, not centres or reference cell
indices. Region and patch names are never physical identifiers. This changes
the extraction version, NOT the accepted error norms or tolerances.
"""

import math
import re
import numpy as np

from .geometry import Mesh, UnsupportedGeometry
from .physics import free_mesh_buoyant as buoyant, free_mesh_shock as shock
from .physics import free_mesh_thermal as thermal
from .physics.completion import Completion
from .physics.evaluation import NativeOutputError
from .physics.foam.parsed import read, canonical
from .physics.foam.science_metrics import field_values, number

VERSION = "polyhedral-observations-v2"


def regions(artifacts, end=None):
    result = []
    topology_seen = False
    for path in artifacts:
        match = re.fullmatch(r"mesh/(?:(.+)/)?points", path)
        if match:
            topology_seen = True
            region = match[1] or ""
            if end is not None:
                try:
                    thermal._field_path(artifacts, "T", end, region)
                except ValueError:
                    continue  # unused mesh used only during construction
            result.append(region)
    if not result:
        if topology_seen:
            raise ValueError("Final temperature field missing for native mesh")
        raise UnsupportedGeometry("Native polyMesh topology was not exported")
    return sorted(result)


class Region:
    def __init__(self, artifacts, name, end, dimensions):
        self.artifacts, self.name, self.end, self.dimensions = (
            artifacts,
            name,
            end,
            dimensions,
        )
        self.cache = {}
        tree = read(self.text("C"))
        tokens = tree.get("internalField", ())
        if tokens[:2] != ("nonuniform", "List<vector>"):
            raise ValueError("Trusted cell-centre export must be explicit")
        n = number(tokens[2])
        if not n.is_integer() or not 0 < n <= 1000000:
            raise ValueError("Invalid native cell count")
        self.count = int(n)
        self.mesh = Mesh.read(artifacts, self.field("C"), self.field("V"), name)

    def text(self, name):
        return self.artifacts[
            thermal._field_path(self.artifacts, name, self.end, self.name)
        ]

    def field(self, name):
        if name not in self.cache:
            self.cache[name] = np.asarray(
                field_values(
                    self.text(name),
                    name,
                    self.count,
                    self.dimensions[name],
                    self.end,
                    region=self.name or None,
                )
            )
        return self.cache[name]

    def boundary(self, name, dimensions):
        tree = read(self.text(name))
        header = tree.get("FoamFile", {})
        loc = header.get("location", ("",))[0].strip('"').split("/")
        if (
            header.get("object") != (name,)
            or header.get("format") != ("ascii",)
            or header.get("class")
            != (("surfaceScalarField",) if name == "phi" else ("volScalarField",))
            or canonical(tree.get("dimensions", ()))
            != canonical(read("d " + dimensions + ";")["d"])
            or len(loc) != (2 if self.name else 1)
            or abs(number(loc[0]) - self.end) > 1e-7
            or (self.name and loc[1] != self.name)
        ):
            raise ValueError("Native boundary field identity/units mismatch: " + name)
        result = np.full(len(self.mesh.faces), np.nan)
        patches = tree.get("boundaryField", {})
        if set(patches) != set(self.mesh.boundary):
            raise ValueError("Native boundary field/mesh patches differ")
        for patch, info in self.mesh.boundary.items():
            start, count = info["start"], info["count"]
            if count:
                result[start : start + count] = thermal._array(
                    patches[patch].get("value", ()), count=count
                )
        return result


def intersection(a, b):
    result = np.column_stack(
        (
            np.maximum(np.asarray(a)[:, 0], np.asarray(b)[:, 0]),
            np.minimum(np.asarray(a)[:, 1], np.asarray(b)[:, 1]),
        )
    )
    return result if np.all(result[:, 1] > result[:, 0] + 1e-14) else None


def physical_bins(task_id):
    """Public physical subvolumes; tuples are axis-aligned boxes, in metres."""
    if task_id == "s-203":
        bins = {"junction": [((0.2, 0.22), (-0.01, 0.01), (0, 0.02))]}
        for i in range(5):
            bins["inlet_" + str(i)] = [
                ((i * 0.04, (i + 1) * 0.04), (-0.01, 0.01), (0, 0.02))
            ]
            bins["lower_" + str(i)] = [
                ((0.2, 0.22), (-0.21 + i * 0.04, -0.21 + (i + 1) * 0.04), (0, 0.02))
            ]
            bins["upper_" + str(i)] = [
                ((0.2, 0.22), (0.01 + i * 0.04, 0.01 + (i + 1) * 0.04), (0, 0.02))
            ]
        return {"": bins}
    h = 0.013333333333333333
    materials = {
        "topAir": [((-0.1, 0.1), (0.008, 0.04), (-0.05, 0.05))],
        "leftSolid": [((-0.1, -h), (0, 0.008), (-0.05, 0.05))],
        "rightSolid": [((h, 0.1), (0, 0.008), (-0.05, 0.05))],
        "heater": [
            ((-h, h), (0, 0.008), (-0.05, 0.05)),
            ((-h, h), (-0.04, 0), (-0.01, 0.01)),
        ],
        "bottomWater": [
            ((-0.1, -h), (-0.04, 0), (-0.05, 0.05)),
            ((h, 0.1), (-0.04, 0), (-0.05, 0.05)),
            ((-h, h), (-0.04, 0), (-0.05, -0.01)),
            ((-h, h), (-0.04, 0), (0.01, 0.05)),
        ],
    }
    result = {}
    for role, boxes in materials.items():
        result[role] = {}
        for x in range(4):
            for z in range(2):
                clip = (
                    (-0.1 + x * 0.05, -0.1 + (x + 1) * 0.05),
                    (-0.04, 0.04),
                    (-0.05 + z * 0.05, -0.05 + (z + 1) * 0.05),
                )
                pieces = [
                    part
                    for box in boxes
                    if (part := intersection(box, clip)) is not None
                ]
                if pieces:
                    result[role][f"{x}_{z}"] = pieces
    return result


def box_volume(box):
    return float(np.prod(np.diff(box, axis=1)))


def weights_for(native, boxes):
    return sum((native.mesh.overlap(box) for box in boxes), np.zeros(native.count))


def require_volume(actual, expected):
    if not math.isclose(actual, expected, rel_tol=2e-6, abs_tol=1e-13):
        raise ValueError(
            f"Physical observation volume missing/duplicated: {actual:.12g} vs {expected:.12g} m3"
        )


def measure(value, unit):
    return {
        "value": value.tolist() if isinstance(value, np.ndarray) else float(value),
        "unit": unit,
    }


def opening_fluxes(natives, task_id):
    """Optional raw-face diagnostics, identified by physical opening planes."""
    result = {}
    try:
        for native in natives:
            mesh = native.mesh
            faces = []
            for face in range(len(mesh.neighbour), len(mesh.faces)):
                centre = mesh.centres[mesh.owner[face]]
                if task_id == "s-202":
                    role = thermal.region_at(centre)
                    if role not in ("topAir", "bottomWater"):
                        continue
                    label = (
                        "minX"
                        if mesh.on_plane(face, 0, -0.1)
                        else "maxX" if mesh.on_plane(face, 0, 0.1) else None
                    )
                else:
                    role = ""
                    label = (
                        "inlet"
                        if mesh.on_plane(face, 0, 0)
                        else (
                            "outlet1"
                            if mesh.on_plane(face, 1, -0.21)
                            else "outlet2" if mesh.on_plane(face, 1, 0.21) else None
                        )
                    )
                if label:
                    faces.append((face, role, label))
            if not faces:
                continue
            q = native.boundary(
                "phi", "[1 0 -1 0 0 0 0]" if task_id == "s-202" else "[0 3 -1 0 0 0 0]"
            )
            t = native.boundary("T", "[0 0 0 1 0 0 0]")
            for face, role, label in faces:
                key = (role + "/" if role else "") + label
                row = result.setdefault(
                    key,
                    {
                        "signed_flow": 0.0,
                        "sensible_enthalpy_outflow_W": 0.0,
                        "flow_unit": "kg/s" if task_id == "s-202" else "m3/s",
                    },
                )
                row["signed_flow"] += float(q[face])
                cp = 4181 if role == "bottomWater" else 1000
                rho = 1.2 if task_id == "s-203" else 1
                row["sensible_enthalpy_outflow_W"] += float(
                    q[face] * rho * cp * (t[face] - 300)
                )
        return (
            {
                "status": "completed",
                "openings": result,
                "note": "Net flux alone is not transient storage balance.",
            }
            if result
            else {
                "status": "not_evaluated",
                "reason": "native_opening_values_unavailable",
            }
        )
    except (ValueError, KeyError):
        return {
            "status": "not_evaluated",
            "reason": "native_boundary_values_unavailable",
        }


def thermal_snapshot(artifacts, task_id, end):
    dimensions = dict(thermal.DIMENSIONS)
    if task_id == "s-203":
        dimensions["p"] = "[0 2 -2 0 0 0 0]"
    natives = [Region(artifacts, n, end, dimensions) for n in regions(artifacts, end)]
    cover = [np.zeros(r.count) for r in natives]
    blocks = {}
    measures = {"final_time": measure(end, "s")}
    for role, bins in physical_bins(task_id).items():
        names = ["T"]
        if role in ("", "bottomWater", "topAir"):
            names += ["U", "p"] + (["p_rgh"] if role else ["k", "epsilon", "nut"])
        blocks[role] = {}
        aggregate = {name: [] for name in names}
        all_weights = []
        for key, boxes in sorted(bins.items()):
            totals = {name: np.zeros(3) if name == "U" else 0.0 for name in names}
            volume = 0.0
            for index, native in enumerate(natives):
                weights = weights_for(native, boxes)
                selected = weights > 0
                cover[index] += weights
                if not selected.any():
                    continue
                volume += float(weights.sum())
                all_weights.extend(weights[selected])
                for name in names:
                    values = native.field(name)[selected]
                    if name == "T" and np.any(values <= 0):
                        raise ValueError("Nonpositive absolute temperature")
                    if role == "topAir" and name == "p" and np.any(values <= 0):
                        raise ValueError("Nonpositive absolute air pressure")
                    if name in ("k", "epsilon", "nut") and np.any(values < -1e-10):
                        raise ValueError("Negative turbulence quantity")
                    totals[name] += np.einsum("i,i...->...", weights[selected], values)
                    aggregate[name].extend(values)
            expected = sum(box_volume(box) for box in boxes)
            require_volume(volume, expected)
            blocks[role][key] = {
                "volume": volume,
                **{
                    n: (
                        (v / volume).tolist()
                        if isinstance(v, np.ndarray)
                        else float(v / volume)
                    )
                    for n, v in totals.items()
                },
            }
        w = np.asarray(all_weights)
        total = w.sum()
        t = np.asarray(aggregate["T"])
        prefix = role + "_" if role else ""
        for name, value, unit in [
            ("volume", total, "m3"),
            ("T_volume_mean", np.dot(t, w) / total, "K"),
            ("T_min_max", np.array([t.min(), t.max()]), "K"),
            ("T_rise_rms", np.sqrt(np.dot((t - 300) ** 2, w) / total), "K"),
        ]:
            measures[prefix + name] = measure(value, unit)
        if "U" in aggregate:
            u = np.asarray(aggregate["U"])
            measures[prefix + "U_volume_mean"] = measure(
                np.einsum("i,ij->j", w, u) / total, "m/s"
            )
            measures[prefix + "speed_volume_rms"] = measure(
                np.sqrt(np.dot(np.sum(u * u, axis=1), w) / total), "m/s"
            )
        if task_id == "s-203":
            measures["temperature_excess_315K"] = measure(
                np.dot(t - 315, w) / total, "K"
            )
        density = (
            1.2
            if task_id == "s-203"
            else (
                1000.0
                if role == "bottomWater"
                else (
                    np.asarray(aggregate["p"]) * 28.9 / (8314.46261815324 * t)
                    if role == "topAir"
                    else 8000.0
                )
            )
        )
        cp = (
            4181.0
            if role == "bottomWater"
            else 1000.0 if role in ("", "topAir") else 450.0
        )
        measures[prefix + "relative_300K_sensible_enthalpy"] = measure(
            np.dot(density * cp * (t - 300), w), "J"
        )
    for native, covered in zip(natives, cover):
        if not np.allclose(covered, native.mesh.volumes, rtol=2e-6, atol=1e-14):
            raise ValueError(
                "Native cells extend outside the supplied material/domain geometry"
            )
    return {
        "version": VERSION,
        "measurements": measures,
        "spatial_volumes": blocks,
        "native_region_count": len(natives),
        "diagnostics": {
            "opening_fluxes": opening_fluxes(natives, task_id),
            "flux_and_energy_balance": {
                "status": "not_evaluated",
                "reason": "not_a_gate_in_accepted_gt_v1",
            },
        },
    }


def single_domain(natives, bounds):
    for native in natives:
        if not np.allclose(
            native.mesh.overlap(bounds), native.mesh.volumes, rtol=2e-6, atol=1e-14
        ):
            raise ValueError("Native cells extend outside supplied geometry")
    require_volume(
        sum(float(r.mesh.volumes.sum()) for r in natives), box_volume(bounds)
    )


def profiles(natives, bounds, axis, bins, fields):
    out = {name: [] for name in fields}
    cuts = np.linspace(*bounds[axis], bins + 1)
    for a, b in zip(cuts, cuts[1:]):
        box = np.asarray(bounds, dtype=float).copy()
        box[axis] = [a, b]
        weights = [n.mesh.overlap(box) for n in natives]
        volume = sum(float(w.sum()) for w in weights)
        require_volume(volume, box_volume(box))
        for name, (field, component) in fields.items():
            total = 0.0
            for native, w in zip(natives, weights):
                values = native.field(field)
                values = values[:, component] if component is not None else values
                total += float(np.dot(w, values))
            out[name].append(total / volume)
    return out


def cavity_heat(natives):
    heat = dict.fromkeys(("hot", "cold", "frontAndBack", "topAndBottom"), 0.0)
    for native in natives:
        values = native.boundary("wallHeatFlux", "[1 0 -3 0 0 0 0]")
        mesh = native.mesh
        for face in range(len(mesh.neighbour), len(mesh.faces)):
            label = None
            for axis, (low, high) in enumerate(buoyant.BOUNDS):
                if mesh.on_plane(face, axis, low) or mesh.on_plane(face, axis, high):
                    label = (
                        ("hot" if mesh.on_plane(face, 0, high) else "cold")
                        if axis == 0
                        else ("topAndBottom" if axis == 1 else "frontAndBack")
                    )
                    break
            if label is not None:
                heat[label] += float(
                    values[face] * np.linalg.norm(mesh.area_vectors[face])
                )
            # Other boundary faces are internal partitions, not external walls.
    return heat


def last_write_change(artifacts, natives, end):
    """Diagnostic only; never silently compare indices on a changed mesh."""
    missing = {
        "status": "not_evaluated",
        "reason": "previous_same_mesh_fields_unavailable",
    }
    if any(
        re.fullmatch(r"[0-9.eE+\-]+/(?:[^/]+/)?polyMesh/(?:points|faces)", p)
        for p in artifacts
    ):
        return {**missing, "reason": "time_varying_mesh_requires_separate_projection"}
    common = None
    for native in natives:
        suffix = (native.name + "/" if native.name else "") + "U"
        available = {
            number(p.split("/")[0])
            for p in artifacts
            if re.fullmatch(r"[0-9.eE+\-]+/" + re.escape(suffix), p)
            and 0 < number(p.split("/")[0]) < end
        }
        common = available if common is None else common & available
    if not common:
        return missing
    prior = max(common)
    t_sum = 0.0
    u_sum = 0.0
    scale = 0.0
    volume = 0.0
    try:
        for native in natives:
            before = {
                name: np.asarray(
                    field_values(
                        artifacts[
                            thermal._field_path(artifacts, name, prior, native.name)
                        ],
                        name,
                        native.count,
                        native.dimensions[name],
                        prior,
                        region=native.name or None,
                    )
                )
                for name in ("T", "U")
            }
            weights = native.mesh.volumes
            t_sum += float(np.dot(weights, np.abs(native.field("T") - before["T"])))
            u_sum += float(
                np.dot(weights, np.sum((native.field("U") - before["U"]) ** 2, axis=1))
            )
            scale += float(np.dot(weights, np.sum(native.field("U") ** 2, axis=1)))
            volume += float(weights.sum())
        return {
            "status": "completed",
            "previous_write": prior,
            "final_write": end,
            "T_relative_change": t_sum / volume / buoyant.DT,
            "U_relative_change": math.sqrt(u_sum / volume)
            / max(math.sqrt(scale / volume), 1e-12),
        }
    except (ValueError, KeyError):
        return missing


def flow_snapshot(artifacts, task_id, end):
    cavity = task_id == "s-204"
    dimensions = buoyant.DIMENSIONS if cavity else shock.DIMENSIONS
    natives = [Region(artifacts, n, end, dimensions) for n in regions(artifacts, end)]
    bounds = buoyant.BOUNDS if cavity else ((-5, 5), (-1, 1), (-1, 1))
    single_domain(natives, bounds)
    data = {
        name: np.concatenate([n.field(name) for n in natives]) for name in dimensions
    }
    v = data["V"]
    volume = float(v.sum())
    u = data["U"]
    t = data["T"]
    p = data["p"]

    def mean(values):
        return np.einsum("i,i...->...", v, np.asarray(values)) / volume

    values = {
        "cell_count": measure(len(v), "1"),
        "volume": measure(volume, "m3"),
        "U_volume_mean": measure(mean(u), "m/s"),
    }
    if cavity:
        values.update(
            {
                "final_iteration": measure(end, "1"),
                "mass": measure(np.dot(v, p / (shock.GAS_R * t)), "kg"),
                "T_volume_mean": measure(mean(t), "K"),
                "p_volume_mean": measure(mean(p), "Pa"),
                "speed_volume_rms": measure(
                    np.sqrt(mean(np.sum(u * u, axis=1))), "m/s"
                ),
            }
        )
        for name, unit in [
            ("k", "m2/s2"),
            ("omega", "1/s"),
            ("nut", "m2/s"),
            ("alphat", "kg/(m s)"),
        ]:
            values[name + "_volume_mean"] = measure(mean(data[name]), unit)
        for axis, label in enumerate(("x", "y")):
            for field, rows in profiles(
                natives, bounds, axis, 20, {"T": ("T", None), "Uy": ("U", 1)}
            ).items():
                values[field + "_" + label + "_bin_mean"] = {
                    "unit": "K" if field == "T" else "m/s",
                    "value": rows,
                }
        heat = cavity_heat(natives)
        values.update(
            {name + "_wall_heat_rate": measure(q, "W") for name, q in heat.items()}
        )
        return {
            "version": VERSION,
            "measurements": values,
            "data": {k: v.tolist() for k, v in data.items()},
            "heat": heat,
            "diagnostics": {
                "heat_balance_relative": abs(sum(heat.values()))
                / max(abs(heat["hot"]), abs(heat["cold"]), 1e-12),
                "last_write_change": last_write_change(artifacts, natives, end),
            },
        }
    rho = data["rho"]
    energy = p / (shock.GAMMA - 1) + 0.5 * rho * np.sum(u * u, axis=1)
    values.update(
        {
            "final_time": measure(end, "s"),
            "mass": measure(np.dot(v, rho), "kg"),
            "axial_momentum": measure(np.dot(v, rho * u[:, 0]), "kg m/s"),
            "total_energy": measure(np.dot(v, energy), "J"),
            "transverse_velocity_rms": measure(
                np.sqrt(mean(np.sum(u[:, 1:] ** 2, axis=1))), "m/s"
            ),
        }
    )
    for field, rows in profiles(
        natives,
        bounds,
        0,
        40,
        {"rho": ("rho", None), "p": ("p", None), "T": ("T", None), "Ux": ("U", 0)},
    ).items():
        values[field + "_axial_bin_mean"] = {"unit": shock.UNITS[field], "value": rows}
    eos = float(np.max(np.abs(p - rho * shock.GAS_R * t) / np.maximum(np.abs(p), 1.0)))
    return {
        "version": VERSION,
        "measurements": values,
        "data": {k: v.tolist() for k, v in data.items()},
        "equation_of_state_relative_max": eos,
        "diagnostics": {"equation_of_state_relative_max": eos},
    }


def snapshot(artifacts, task_id):
    try:
        log = artifacts.get("solver.log", "")
        if task_id == "s-204":
            end, last = buoyant.last_iteration(log)
        else:
            end = {"s-202": 100.0, "s-203": 1.5, "s-205": 0.007}[task_id]
            if not Completion((), "transient", end, 1e-7, False, (), 300).completed(
                log
            ):
                raise ValueError("Actual completed final native time not proven")
            last = log[list(re.finditer(r"^Time = ", log, re.M))[-1].end() :]
        result = (
            thermal_snapshot(artifacts, task_id, end)
            if task_id in ("s-202", "s-203")
            else flow_snapshot(artifacts, task_id, end)
        )
        rows = re.findall(
            r"Solving for (\w+), Initial residual = ([^,\s]+), Final residual = ([^,\s]+)",
            last,
        )
        result["diagnostics"]["final_residuals"] = {
            n: {"initial": number(a), "final": number(b)} for n, a, b in rows
        }
        result["diagnostics"]["missing_residuals_are_not_zero"] = True
        return result
    except UnsupportedGeometry:
        raise
    except (ValueError, KeyError, IndexError) as exc:
        raise NativeOutputError(str(exc)) from exc
