"""Pure numeric extraction/comparison migrated from free_mesh_flow; no runtime policy."""
import numpy as np
from .foam.parsed import read, tokens, list_dictionary
from .foam.science_metrics import number
from .tutorial_tasks import list_values

def _mesh_payload(text, expected_object):
    data = tokens(text)
    if len(data) < 4 or data[0].text != 'FoamFile' or data[1].text != '{':
        raise ValueError('Native mesh header missing')
    depth, index = 1, 2
    while depth and index < len(data):
        depth += (data[index].text == '{')-(data[index].text == '}')
        index += 1
    header = read(text[:data[index-1].end])['FoamFile']
    if header.get('format') != ('ascii',) or header.get('object') != (expected_object,):
        raise ValueError('Native mesh object/format mismatch')
    size = number(data[index].text)
    if not size.is_integer() or size < 0:
        raise ValueError('Invalid native mesh list size')
    payload = tuple(row.text for row in data[index+1:])
    if not payload or payload[0] != '(' or payload[-1] != ')':
        raise ValueError('Native mesh list is incomplete')
    return int(size), payload

def native_boundary_area_vectors(artifacts):
    """Actual generated faces, not inferred uniform cell face areas."""
    npoints, point_tokens = _mesh_payload(artifacts['mesh/points'], 'points')
    points = np.asarray([[number(x) for x in row] for row in list_values(point_tokens)])
    if points.shape != (npoints, 3):
        raise ValueError('Native mesh points shape mismatch')
    nfaces, face_tokens = _mesh_payload(artifacts['mesh/faces'], 'faces')
    rows = list_values(face_tokens)
    faces = []
    if len(rows) != 2*nfaces:
        raise ValueError('Native face list count mismatch')
    for index in range(0, len(rows), 2):
        count, ids = int(rows[index]), rows[index+1]
        if count != len(ids) or count < 3:
            raise ValueError('Native face vertex count mismatch')
        ids = [int(v) for v in ids]
        if any(v < 0 or v >= npoints for v in ids):
            raise ValueError('Native face references an unknown point')
        vertices = points[ids]
        face = np.cross(vertices[1:-1]-vertices[0], vertices[2:]-vertices[0]).sum(axis=0)/2
        if not np.isfinite(face).all() or np.linalg.norm(face) <= 0:
            raise ValueError('Native face has invalid oriented area')
        faces.append(face.tolist())
    npatches, boundary_tokens = _mesh_payload(artifacts['mesh/boundary'], 'boundary')
    boundary = list_dictionary(boundary_tokens)
    if len(boundary) != npatches:
        raise ValueError('Native patch count mismatch')
    result = {}
    for name, value in boundary.items():
        start, count = int(value['startFace'][0]), int(value['nFaces'][0])
        if start < 0 or count < 0 or start+count > len(faces):
            raise ValueError('Native patch indexes outside face list')
        result[name] = faces[start:start+count]
    return result
