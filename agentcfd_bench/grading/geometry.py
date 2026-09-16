"""Polyhedral cell/box intersections from native points/faces/owner/neighbour.

No cell-order, hexahedral-grid or patch-name assumptions. Oriented face pyramids
form a signed tetrahedral decomposition; clipping each convex tetrahedron also
handles non-convex cells through signed cancellation. Fully contained cells use
their independently exported native volume. No nearest-centre bin assignment.
"""

from dataclasses import dataclass
import math
import numpy as np

from .physics.free_mesh_flow import _mesh_payload
from .physics.foam.parsed import list_dictionary
from .physics.tutorial_tasks import list_values


class UnsupportedGeometry(ValueError):
    """An extraction representation limitation, never a physical failure."""


def clip_polygon(polygon, axis, bound, keep_lower):
    result = []
    cuts = []
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        da = (a[axis] - bound) * (1 if keep_lower else -1)
        db = (b[axis] - bound) * (1 if keep_lower else -1)
        if da <= 0:
            result.append(a)
        if (da < 0 < db) or (db < 0 < da):
            point = a + (b - a) * (da / (da - db))
            point[axis] = bound
            result.append(point)
            cuts.append(point)
        elif da == 0:
            cuts.append(a)
    return np.asarray(result), cuts


def clipped_tetra_volume(vertices, box):
    """Exact linear-polyhedron clipping (floating-point roundoff only)."""
    lo, hi = box[:, 0], box[:, 1]
    if np.any(vertices.max(axis=0) <= lo) or np.any(vertices.min(axis=0) >= hi):
        return 0.0
    determinant = abs(np.linalg.det((vertices[1:] - vertices[0]).T)) / 6
    if np.all(vertices >= lo) and np.all(vertices <= hi):
        return determinant
    faces = [
        vertices[list(ids)] for ids in ((0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2))
    ]
    for axis in range(3):
        for bound, keep_lower in ((lo[axis], False), (hi[axis], True)):
            coordinates = np.concatenate(faces)[:, axis]
            # An existing coplanar face is already the cap. Do not duplicate it.
            if (keep_lower and np.all(coordinates <= bound)) or (
                not keep_lower and np.all(coordinates >= bound)
            ):
                continue
            new = []
            cuts = []
            for face in faces:
                polygon, points = clip_polygon(face, axis, bound, keep_lower)
                if len(polygon) >= 3:
                    new.append(polygon)
                cuts.extend(points)
            if not new:
                return 0.0
            # Crossings shared by neighbouring faces must yield one cap vertex.
            unique = []
            for point in cuts:
                if not any(
                    np.linalg.norm(point - old)
                    <= 1e-13 * max(1.0, np.linalg.norm(point))
                    for old in unique
                ):
                    unique.append(point)
            if len(unique) >= 3:
                cap = np.asarray(unique)
                centre = cap.mean(axis=0)
                axes = [i for i in range(3) if i != axis]
                angles = np.arctan2(
                    cap[:, axes[1]] - centre[axes[1]], cap[:, axes[0]] - centre[axes[0]]
                )
                new.append(cap[np.argsort(angles)])
            faces = new
    centre = np.concatenate(faces).mean(axis=0)
    volume = 0.0
    for face in faces:
        volume += sum(
            abs(np.dot(face[0] - centre, np.cross(a - centre, b - centre))) / 6
            for a, b in zip(face[1:-1], face[2:])
        )
    return float(volume)


@dataclass
class Mesh:
    points: np.ndarray
    faces: list
    owner: np.ndarray
    neighbour: np.ndarray
    boundary: dict
    centres: np.ndarray
    volumes: np.ndarray

    def __post_init__(self):
        self.points = np.asarray(self.points, dtype=float)
        self.owner = np.asarray(self.owner, dtype=int)
        self.neighbour = np.asarray(self.neighbour, dtype=int)
        self.centres = np.asarray(self.centres, dtype=float)
        self.volumes = np.asarray(self.volumes, dtype=float)
        count = len(self.volumes)
        nf = len(self.faces)
        if (
            self.points.ndim != 2
            or self.points.shape[1] != 3
            or self.centres.shape != (count, 3)
            or len(self.owner) != nf
            or len(self.neighbour) > nf
            or count == 0
            or not np.isfinite(self.points).all()
            or not np.isfinite(self.centres).all()
            or not np.isfinite(self.volumes).all()
            or np.any(self.volumes <= 0)
            or np.any(self.owner < 0)
            or np.any(self.owner >= count)
            or np.any(self.neighbour < 0)
            or np.any(self.neighbour >= count)
        ):
            raise ValueError("Invalid native mesh connectivity/geometry")
        self.face_centres = np.zeros((nf, 3))
        self.area_vectors = np.zeros((nf, 3))
        self.face_low = np.zeros((nf, 3))
        self.face_high = np.zeros((nf, 3))
        self.low = np.full((count, 3), np.inf)
        self.high = np.full((count, 3), -np.inf)
        groups = {}
        for i, face in enumerate(self.faces):
            if len(face) < 3 or min(face) < 0 or max(face) >= len(self.points):
                raise ValueError("Invalid face vertex indices")
            groups.setdefault(len(face), []).append(i)
        for indices in groups.values():
            ids = np.asarray(indices)
            vertices = self.points[np.asarray([self.faces[i] for i in ids])]
            average = vertices.mean(axis=1)
            cross = np.cross(
                vertices - average[:, None, :],
                np.roll(vertices, -1, axis=1) - average[:, None, :],
            )
            weights = np.linalg.norm(cross, axis=2)
            if np.any(weights.sum(axis=1) <= 0):
                raise ValueError("Degenerate native face")
            tri_centres = (
                vertices + np.roll(vertices, -1, axis=1) + average[:, None, :]
            ) / 3
            self.face_centres[ids] = (tri_centres * weights[:, :, None]).sum(
                axis=1
            ) / weights.sum(axis=1)[:, None]
            self.area_vectors[ids] = cross.sum(axis=1) / 2
            self.face_low[ids] = vertices.min(axis=1)
            self.face_high[ids] = vertices.max(axis=1)
        np.minimum.at(self.low, self.owner, self.face_low)
        np.maximum.at(self.high, self.owner, self.face_high)
        internal = len(self.neighbour)
        np.minimum.at(self.low, self.neighbour, self.face_low[:internal])
        np.maximum.at(self.high, self.neighbour, self.face_high[:internal])
        contributions = (
            np.einsum(
                "ij,ij->i",
                self.area_vectors,
                self.face_centres - self.centres[self.owner],
            )
            / 3
        )
        recovered = np.bincount(self.owner, weights=contributions, minlength=count)
        if internal:
            contributions = (
                -np.einsum(
                    "ij,ij->i",
                    self.area_vectors[:internal],
                    self.face_centres[:internal] - self.centres[self.neighbour],
                )
                / 3
            )
            recovered += np.bincount(
                self.neighbour, weights=contributions, minlength=count
            )
        if not np.allclose(recovered, self.volumes, rtol=2e-5, atol=1e-15):
            raise UnsupportedGeometry(
                "Native polyhedron decomposition does not reproduce exported cell volumes"
            )
        closure = np.zeros((count, 3))
        np.add.at(closure, self.owner, self.area_vectors)
        np.add.at(closure, self.neighbour, -self.area_vectors[:internal])
        if np.any(
            np.linalg.norm(closure, axis=1) > 1e-6 * self.volumes ** (2 / 3) + 1e-14
        ):
            raise UnsupportedGeometry("Native cell surface is not closed")
        # Proven orthogonal boxes get an exact fast path; all other cells still
        # use their real polyhedra. This is an optimization, not an eligibility rule.
        axis_faces = np.any(self.face_high - self.face_low <= 1e-12, axis=1)
        non_axis = np.bincount(self.owner, weights=~axis_faces, minlength=count)
        non_axis += np.bincount(
            self.neighbour, weights=~axis_faces[:internal], minlength=count
        )
        bbox_volume = np.prod(self.high - self.low, axis=1)
        self.boxes = (non_axis == 0) & np.isclose(
            bbox_volume, self.volumes, rtol=2e-5, atol=1e-16
        )
        coverage = np.zeros(nf - internal, dtype=int)
        for patch in self.boundary.values():
            start, count_faces = patch["start"], patch["count"]
            if start < internal or count_faces < 0 or start + count_faces > nf:
                raise ValueError("Invalid boundary face range")
            coverage[start - internal : start - internal + count_faces] += 1
        if not np.all(coverage == 1):
            raise ValueError("Boundary faces missing or duplicated")
        self._cell_faces = None
        self._tetra_cache = {}
        self._overlap_cache = {}

    @classmethod
    def read(cls, artifacts, centres, volumes, region=""):
        prefix = "mesh/" + (region + "/" if region else "")

        def payload(name):
            if prefix + name not in artifacts:
                raise UnsupportedGeometry("Native mesh topology missing: " + name)
            n, raw = _mesh_payload(artifacts[prefix + name], name)
            rows = list_values(raw)
            return n, rows, raw

        n, rows, _ = payload("points")
        points = np.asarray(rows, dtype=float)
        if len(points) != n:
            raise ValueError("Mesh point count mismatch")
        nf, rows, _ = payload("faces")
        if len(rows) != nf * 2:
            raise ValueError("Mesh face count mismatch")
        faces = []
        for i in range(nf):
            size = int(rows[2 * i])
            ids = list(map(int, rows[2 * i + 1]))
            if size != len(ids):
                raise ValueError("Face size mismatch")
            faces.append(ids)
        labels = []
        for name in ("owner", "neighbour"):
            n, rows, _ = payload(name)
            if len(rows) != n:
                raise ValueError("Connectivity label count mismatch")
            labels.append(np.asarray(rows, dtype=int))
        npatches, _, raw = payload("boundary")
        tree = list_dictionary(raw)
        if len(tree) != npatches:
            raise ValueError("Boundary patch count mismatch")
        boundary = {
            name.strip('"'): {
                "start": int(v["startFace"][0]),
                "count": int(v["nFaces"][0]),
                "type": v["type"][0],
            }
            for name, v in tree.items()
        }
        return cls(points, faces, *labels, boundary, centres, volumes)

    def tetrahedra(self, cell):
        if cell in self._tetra_cache:
            return self._tetra_cache[cell]
        if self._cell_faces is None:
            self._cell_faces = [[] for _ in self.volumes]
            for face, owner in enumerate(self.owner):
                self._cell_faces[owner].append((face, 1))
            for face, other in enumerate(self.neighbour):
                self._cell_faces[other].append((face, -1))
        result = []
        for face, orientation in self._cell_faces[cell]:
            vertices = self.points[self.faces[face]]
            fc = self.face_centres[face]
            c = self.centres[cell]
            for a, b in zip(vertices, np.roll(vertices, -1, axis=0)):
                tet = np.asarray([c, fc, a, b])
                signed = np.linalg.det((tet[1:] - c).T) / 6 * orientation
                if abs(signed) > 1e-25:
                    result.append((tet, math.copysign(1.0, signed)))
        self._tetra_cache[cell] = result
        return result

    def overlap(self, box):
        box = np.asarray(box, dtype=float)
        key = tuple(box.ravel())
        if key in self._overlap_cache:
            return self._overlap_cache[key]
        if box.shape != (3, 2) or np.any(box[:, 0] >= box[:, 1]):
            raise ValueError("Nonempty 3D observation box required")
        tolerance = 1e-12
        outside = np.any(self.high <= box[:, 0] + tolerance, axis=1) | np.any(
            self.low >= box[:, 1] - tolerance, axis=1
        )
        inside = (
            np.all(self.low >= box[:, 0] - tolerance, axis=1)
            & np.all(self.high <= box[:, 1] + tolerance, axis=1)
            & ~outside
        )
        weights = np.zeros(len(self.volumes))
        weights[inside] = self.volumes[inside]
        partial = ~outside & ~inside
        boxes = partial & self.boxes
        weights[boxes] = (
            np.prod(
                np.maximum(
                    0,
                    np.minimum(self.high[boxes], box[:, 1])
                    - np.maximum(self.low[boxes], box[:, 0]),
                ),
                axis=1,
            )
            * self.volumes[boxes]
            / np.prod(self.high[boxes] - self.low[boxes], axis=1)
        )
        for cell in np.flatnonzero(partial & ~self.boxes):
            weights[cell] = sum(
                sign * clipped_tetra_volume(tet, box)
                for tet, sign in self.tetrahedra(cell)
            )
        if np.any(weights < -1e-7 * self.volumes) or np.any(
            weights > self.volumes * (1 + 1e-6)
        ):
            raise UnsupportedGeometry("Inconsistent signed polyhedral intersection")
        weights = np.maximum(0, np.minimum(weights, self.volumes))
        self._overlap_cache[key] = weights
        return weights

    def on_plane(self, face, axis, value, tolerance=1e-8):
        return (
            abs(self.face_low[face, axis] - value) < tolerance
            and abs(self.face_high[face, axis] - value) < tolerance
        )
