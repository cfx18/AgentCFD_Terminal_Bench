"""Export selected, accepted native results as neutral dense observations.

Run once per new draft: python -m agentcfd_bench.tasks.reconstruction TASK_ROOT
This never solves, calls a model, overwrites historical data, or releases a task.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from ..grading.dense import COLUMNS, POLICY
from ..grading.physics.foam.science_metrics import field_values
from ..records.store import write_once


def legacy_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def export(task_root, project):
    task_root, project = Path(task_root), Path(project)
    for task_id in ('s-203', 's-204'):
        task = task_root / task_id
        if (task / 'public/observations').exists() or (task / 'private/reference.json').exists():
            raise FileExistsError('Create a new version; observations already exist: ' + str(task))
        if not (task / 'public/instruction.md').is_file():
            raise ValueError('Reviewed author instruction template missing')
    reports = []
    for task_id in ('s-203', 's-204'):
        task = task_root / task_id
        manifest = project / 'tasks/releases/expert-output-v1' / task_id / 'solution/accepted-target.json'
        reference = json.loads(manifest.read_text())
        source = Path(reference['source']['run_directory'])
        result = json.loads((source / 'result.json').read_text())['payload']
        if (reference['reference_status'] != 'accepted_by_expert'
                or result['verdict'] != 'pass'
                or json.loads((source / 'released.json').read_text())['payload'] != {'released': True}
                or legacy_digest(result) != reference['source']['result_hash']
                or legacy_digest(result['artifacts']) != reference['source']['artifact_hash']):
            raise ValueError('Selected native evidence identity mismatch')
        end = reference['source']['endpoint']['value']
        count = int(reference['observations']['measurements']['cell_count']['value'])
        artifacts = result['artifacts']
        pressure_dims = '[0 2 -2 0 0 0 0]' if task_id == 's-203' else '[1 -1 -2 0 0 0 0]'
        dimensions = {'C': '[0 1 0 0 0 0 0]', 'V': '[0 3 0 0 0 0 0]',
                      'U': '[0 1 -1 0 0 0 0]', 'p': pressure_dims, 'T': '[0 0 0 1 0 0 0]'}
        arrays = {}
        for name, dims in dimensions.items():
            paths = [p for p in artifacts if re.fullmatch(r'[0-9.eE+\-]+/' + name, p)
                     and abs(float(p.split('/')[0]) - end) < 1e-8]
            if len(paths) != 1:
                raise ValueError('Missing/ambiguous native observation: ' + name)
            arrays[name] = np.asarray(field_values(artifacts[paths[0]], name, count, dims, end))
        data = np.column_stack((arrays['C'], arrays['V'], arrays['U'], arrays['p'], arrays['T']))
        if not np.isfinite(data).all() or np.any(arrays['V'] <= 0):
            raise ValueError('Invalid source observations')
        public = task / 'public'
        (public / 'observations').mkdir()
        csv_path = public / 'observations/fields.csv'
        with csv_path.open('x') as out:
            np.savetxt(out, data, delimiter=',', header=','.join(COLUMNS), comments='', fmt='%.17g')
        p_unit = 'm2/s2' if task_id == 's-203' else 'Pa'
        schema = {
            'schema': POLICY, 'synthetic_observations': True, 'point_count': count,
            'columns': list(COLUMNS), 'coordinate_unit': 'm', 'weight_unit': 'm3',
            'velocity_unit': 'm/s', 'temperature_unit': 'K', 'pressure_unit': p_unit,
            'pressure_definition': 'kinematic gauge pressure' if task_id == 's-203' else 'absolute thermodynamic pressure',
            'snapshot': {'kind': 'physical_time', 'value': 1.5, 'unit': 's'} if task_id == 's-203' else
                        {'kind': 'finite_numerical_reference', 'physical_time': None,
                         'note': 'One accepted finite numerical state, not a certified steady or mesh-independent solution.'},
            'normalizers': {
                'U': {'value': float(np.sqrt(np.average(np.sum(arrays['U'] ** 2, axis=1), weights=arrays['V']))),
                      'unit': 'm/s', 'definition': 'reference volume-weighted RMS speed'},
                'T': {'value': float(np.ptp(arrays['T'])), 'unit': 'K',
                      'definition': 'reference maximum minus minimum temperature, NOT absolute Kelvin'},
                'p': {'value': float(np.ptp(arrays['p'])), 'unit': p_unit,
                      'definition': 'reference maximum minus minimum pressure, NOT absolute mean'},
            },
            'sampling': 'All reference internal-cell centres; candidate samples use native containing-cell values at these coordinates.',
            'csv_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            'scoring_status': 'draft_raw_metrics_only; thresholds_and_reward_not_released',
        }
        if any(v['value'] <= 0 for v in schema['normalizers'].values()):
            raise ValueError('Degenerate normalization requires expert decision')
        write_once(public / 'observations/schema.json', schema)
        geometry = (project / 'tasks/releases/workbench-v3' / task_id / 'public/geometry/domain.stl').read_text()
        # Only exterior geometry: remove hot/cold/inlet/outlet names and preserve triangles.
        names = list(dict.fromkeys(re.findall(r'^solid (.+)$', geometry, re.M)))
        mapping = {name: f'surface_{i + 1:02d}' for i, name in enumerate(names)}
        geometry = re.sub(r'^(solid|endsolid) (.+)$', lambda m: m[1] + ' ' + mapping[m[2]], geometry, flags=re.M)
        (public / 'geometry').mkdir(exist_ok=True)
        with (public / 'geometry/domain.stl').open('x') as out:
            out.write(geometry)
        private = {'schema': POLICY, 'task_id': task_id, 'reference_status': 'accepted_by_expert',
                   'source_manifest': str(manifest), 'source': reference['source'],
                   'public_csv_sha256': schema['csv_sha256'], 'surface_names': mapping,
                   'endpoint_kind': 'physical_time' if task_id == 's-203' else 'latest_saved_state',
                   'required_time': 1.5 if task_id == 's-203' else None,
                   'dimensions': {k: v for k, v in dimensions.items() if k in ('U', 'T', 'p')}}
        write_once(task / 'private/reference.json', private)
        reports.append({'task': task_id, 'points': count, 'normalizers': schema['normalizers'],
                        'source_result_hash': reference['source']['result_hash'], 'csv_sha256': schema['csv_sha256']})
    return {'tasks': reports, 'paid_calls': 0, 'solver_runs': 0, 'release_status': 'draft'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task_root', type=Path)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(json.dumps(export(args.task_root, args.project), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
