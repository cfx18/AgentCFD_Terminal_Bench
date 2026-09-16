"""Mesh-independent dense-observation metrics. No solver, model, or scheduling.

Coordinates refer to physical points, never candidate cell indices. Native
sampling is performed separately. Thresholds/reward remain unset until reviewed.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

COLUMNS = ('x_m', 'y_m', 'z_m', 'volume_m3', 'Ux_m_s', 'Uy_m_s', 'Uz_m_s', 'p', 'T_K')
POLICY = 'dense-observation-v1'


class InvalidNativeSamples(ValueError):
    """Invalid candidate values, not corrupt reference data or grader failure."""


def observations(public):
    public = Path(public)
    schema = json.loads((public / 'observations/schema.json').read_text())
    if schema.get('schema') != POLICY:
        raise ValueError('Unsupported observation schema')
    path = public / 'observations/fields.csv'
    if hashlib.sha256(path.read_bytes()).hexdigest() != schema['csv_sha256']:
        raise ValueError('Observation CSV changed')
    with path.open() as stream:
        if tuple(stream.readline().strip().split(',')) != COLUMNS:
            raise ValueError('Observation columns differ from schema')
    data = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2)
    if data.shape != (schema['point_count'], len(COLUMNS)) or not np.isfinite(data).all():
        raise ValueError('Incomplete/nonfinite observation data')
    if np.any(data[:, 3] <= 0) or len(np.unique(data[:, :3], axis=0)) != len(data):
        raise ValueError('Invalid observation weights or duplicate points')
    return schema, data


def align_samples(coordinates, values, target_points, *, tolerance=1e-9):
    """Accept row reordering, reject missing/outside/duplicate or shifted samples.

    Native cloud sampling preserves requested coordinates even on a new mesh.
    Rounding is for a deterministic join, NOT nearest-neighbour extrapolation.
    """
    points = np.asarray(coordinates, dtype=float)
    values = np.asarray(values, dtype=float)
    target = np.asarray(target_points, dtype=float)
    if points.shape != target.shape or points.ndim != 2 or points.shape[1] != 3:
        raise ValueError('Missing observation points: complete coverage required')
    if len(values) != len(points) or not np.isfinite(points).all() or not np.isfinite(values).all():
        raise ValueError('Invalid/nonfinite native samples')
    def index(rows):
        keys = [tuple(row) for row in np.round(rows, 9)]
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate or unresolved observation coordinates')
        return {key: i for i, key in enumerate(keys)}
    source, wanted = index(points), index(target)
    if source.keys() != wanted.keys():
        raise ValueError('Native sample coordinates do not match requested points')
    order = [source[key] for key in wanted]
    if np.max(np.abs(points[order] - target)) > tolerance:
        raise ValueError('Native sample coordinate error exceeds tolerance')
    return values[order]


def compare(data, predicted, schema):
    """Return raw and normalized errors; do not invent a pass threshold or reward."""
    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or data.shape[1] != len(COLUMNS) or not np.isfinite(data).all():
        raise ValueError('Invalid reference array')
    w = data[:, 3]
    if np.any(w <= 0):
        raise ValueError('Positive reference-volume weights required')
    w = w / w.sum()
    truth = {'U': data[:, 4:7], 'p': data[:, 7], 'T': data[:, 8]}
    if set(predicted) != set(truth):
        raise InvalidNativeSamples('All and only U, p and T are required')
    metrics = {}
    for name, reference in truth.items():
        values = np.asarray(predicted[name], dtype=float)
        if values.shape != reference.shape or not np.isfinite(values).all():
            raise InvalidNativeSamples('Invalid native field samples: ' + name)
        if name == 'T' and np.any(values <= 0):
            raise InvalidNativeSamples('Nonpositive absolute temperature')
        try:
            with np.errstate(over='raise', invalid='raise'):
                delta = values - reference
                magnitude = np.linalg.norm(delta, axis=1) if name == 'U' else abs(delta)
                rmse = float(np.sqrt(np.dot(w, magnitude ** 2)))
        except FloatingPointError as exc:
            raise InvalidNativeSamples('Native sample error exceeds numeric range: ' + name) from exc
        scale = float(schema['normalizers'][name]['value'])
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError('Invalid frozen normalization scale')
        metrics[name] = {
            'unit': schema['normalizers'][name]['unit'],
            'rmse': rmse, 'maximum_absolute_error': float(magnitude.max()),
            'normalized_rmse': rmse / scale,
            'normalized_maximum_error': float(magnitude.max()) / scale,
            'normalizer': scale,
        }
        if name != 'U':
            metrics[name]['mean_bias'] = float(np.dot(w, delta))
        if name == 'p':
            aligned = delta - np.dot(w, delta)
            metrics[name]['gauge_aligned_rmse'] = float(np.sqrt(np.dot(w, aligned ** 2)))
            metrics[name]['gauge_aligned_maximum_error'] = float(np.max(abs(aligned)))
            metrics[name]['note'] = 'Raw absolute/gauge offset and spatial shape are reported separately; no offset silently removed.'
    return {
        'verdict': 'not_evaluated', 'reason': 'dense_rubric_pending_review',
        'metric_status': 'completed', 'policy': POLICY, 'reward': None,
        'point_count': len(data), 'coverage': 1.0, 'metrics': metrics,
        'convergence_certified': False, 'mechanism_identification_scored': False,
        'integrity_review_required': True,
    }
