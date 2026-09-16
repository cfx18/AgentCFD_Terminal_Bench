import numpy as np
import pytest

from agentcfd_bench.grading.geometry import (
    Mesh,
    UnsupportedGeometry,
    clipped_tetra_volume,
)


def prism(polygon, *, shear=0):
    """Extrude a CCW polygon; allow concave bases and skew side faces."""
    xy = np.asarray(polygon, dtype=float)
    n = len(xy)
    points = np.array([[x, y, 0] for x, y in xy] + [[x + shear, y, 1] for x, y in xy])
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    faces.extend([[i, (i + 1) % n, (i + 1) % n + n, i + n] for i in range(n)])
    cross = xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1]
    area = cross.sum() / 2
    centre = ((xy + np.roll(xy, -1, axis=0)) * cross[:, None]).sum(axis=0) / (6 * area)
    return Mesh(
        points,
        faces,
        np.zeros(n + 2, dtype=int),
        [],
        {"arbitrary": {"start": 0, "count": n + 2, "type": "wall"}},
        [[centre[0] + shear / 2, centre[1], 0.5]],
        [area],
    )


def test_tetra_clips_and_coplanar_cap_not_duplicated():
    tet = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    assert clipped_tetra_volume(
        tet, np.array([[0, 1], [0, 1], [0, 1]])
    ) == pytest.approx(1 / 6)
    assert clipped_tetra_volume(
        tet, np.array([[0, 0.5], [0, 1], [0, 1]])
    ) == pytest.approx(7 / 48)
    assert clipped_tetra_volume(
        tet, np.array([[0.5, 1], [0, 1], [0, 1]])
    ) == pytest.approx(1 / 48)


@pytest.mark.parametrize("shear", [0, 0.3, -0.2])
def test_skew_mesh_partition_conserves_volume(shear):
    mesh = prism([(0, 0), (1, 0), (1, 1), (0, 1)], shear=shear)
    assert bool(mesh.boxes[0]) == (shear == 0)
    cuts = np.linspace(-0.5, 1.5, 17)
    parts = [
        mesh.overlap([[a, b], [-1, 2], [-1, 2]])[0] for a, b in zip(cuts, cuts[1:])
    ]
    assert sum(parts) == pytest.approx(1, abs=1e-12)
    assert mesh.overlap([[-1, 2], [-1, 2], [0, 0.37]])[0] == pytest.approx(
        0.37, abs=1e-12
    )


def test_concave_polyhedron_signed_decomposition():
    mesh = prism([(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)])
    assert not mesh.boxes[0]
    assert mesh.overlap([[1, 2], [1, 2], [0, 1]])[0] == pytest.approx(0, abs=1e-12)
    assert mesh.overlap([[0, 1.5], [0, 1.5], [0, 1]])[0] == pytest.approx(2, abs=1e-12)
    assert mesh.overlap([[0, 2], [0, 2], [0, 0.4]])[0] == pytest.approx(1.2, abs=1e-12)


def test_forged_native_volume_is_not_accepted():
    good = prism([(0, 0), (1, 0), (1, 1), (0, 1)])
    with pytest.raises(UnsupportedGeometry):
        Mesh(good.points, good.faces, good.owner, [], good.boundary, good.centres, [2])
