"""Trusted native point sampling; never advances time or fits a surrogate mesh.

The sampler receives coordinates, not target values. It runs in the same isolated
native image; no GT/grader/credentials are mounted. Only frozen fields are read.
"""
import gzip
import json
from pathlib import Path
import re
import shutil
import time
import uuid

import numpy as np

from .dense import observations, align_samples, compare, InvalidNativeSamples
from ..execution.files import inventory
from ..execution.runner import Runner
from ..records.store import digest, read, write_once


class InvalidNativeFields(ValueError):
    """Missing/wrong candidate data, distinct from a sampler infrastructure error."""


def select_time(case, reference):
    case = Path(case)
    names = [p.name for p in case.iterdir() if p.is_dir()
             and re.fullmatch(r'[0-9]+(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?', p.name)]
    if reference['endpoint_kind'] == 'physical_time':
        names = [n for n in names if abs(float(n) - reference['required_time']) < 1e-8]
    else:
        names = [n for n in names if float(n) > 0]
        names = [n for n in names if float(n) == max(map(float, names))] if names else []
    if len(names) != 1:
        raise InvalidNativeFields('Missing or ambiguous target output time')
    stamp = names[0]
    for name, expected in reference['dimensions'].items():
        candidates = [case / stamp / name, case / stamp / (name + '.gz')]
        present = [p for p in candidates if p.is_file()]
        if len(present) != 1:
            raise InvalidNativeFields('Missing or ambiguous native field: ' + name)
        opener = gzip.open if present[0].suffix == '.gz' else open
        with opener(present[0], 'rb') as stream:
            head = stream.read(16384).split(b'internalField', 1)[0].decode('ascii', errors='replace')
        dims = re.search(r'\bdimensions\s*\[([^]]+)\]\s*;', head)
        if not dims or tuple(dims[1].split()) != tuple(expected.strip('[]').split()):
            raise InvalidNativeFields('Wrong native dimensions for ' + name)
        kind = 'volVectorField' if name == 'U' else 'volScalarField'
        if not re.search(r'\bclass\s+' + kind + r'\s*;', head):
            raise InvalidNativeFields('Wrong native field class for ' + name)
        if not re.search(r'\bobject\s+' + name + r'\s*;', head):
            raise InvalidNativeFields('Wrong native field object for ' + name)
    return stamp


def sampling_dictionary(points, namespace):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('Finite physical sample coordinates required')
    if not re.fullmatch(r'dense_[a-f0-9]{16}', namespace):
        raise ValueError('Invalid trusted sampler namespace')
    coordinates = '\n'.join('(' + ' '.join(format(v, '.17g') for v in row) + ')' for row in points)
    header = 'FoamFile {version 2.0; format ascii; class dictionary; object denseSampling;}\nfunctions\n{\n'
    blocks = []
    for name in ('T', 'p', 'U'):
        blocks.append(f'''{namespace}_{name}
{{
    type sets;
    libs ("libsampling.so");
    enabled true;
    writeControl timeStep;
    writeInterval 1;
    writePrecision 17;
    interpolationScheme cell;
    setFormat raw;
    fields ({name});
    sets (cloud {{type cloud; axis xyz; points (\n{coordinates}\n);}});
}}
''')
    return header + '\n'.join(blocks) + '}\n'


def sample_case(case, public, reference, sandbox, output, *, seconds=300):
    """Sample a frozen case. Existing dispatches are observed, never reissued."""
    case, output = Path(case), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    schema, targets = observations(public)
    stamp = select_time(case, reference)
    identity = {'case': digest(inventory(case)), 'observations': schema['csv_sha256'],
                'time': stamp, 'dimensions': reference['dimensions']}
    intent = output / 'sampling-plan.json'
    work = output / 'work'
    if intent.exists():
        plan = read(intent)
        if plan['identity'] != identity:
            raise ValueError('Cannot reuse sampling evidence for changed inputs')
    else:
        namespace = 'dense_' + uuid.uuid4().hex[:16]
        plan = {'identity': identity, 'namespace': namespace}
        write_once(intent, plan)
    namespace = plan['namespace']
    binding = output / 'operation.json'
    dispatched = output / 'dispatch-intent.json'
    exports = Runner(output / 'native', sandbox, seconds=seconds)
    if binding.exists():
        operation = read(binding)
    else:
        if dispatched.exists():
            raise RuntimeError('Sampling dispatch outcome unknown; do not replay')
        # These are replaceable preparation files; original case is never edited.
        shutil.copytree(case, work, dirs_exist_ok=True)
        # A measurement does not need the candidate's runtime hooks or schemes.
        # Leave frozen submission evidence untouched; sanitize this export copy.
        for filename, body in {
            'controlDict': 'application postProcess; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1; writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 17; runTimeModifiable false;',
            'fvSchemes': 'ddtSchemes {default Euler;} gradSchemes {default Gauss linear;} divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;}',
            'fvSolution': 'solvers {}',
        }.items():
            (work / 'system' / filename).write_text(
                'FoamFile {version 2.0; format ascii; class dictionary; object ' + filename + ';}\n' + body + '\n')
        name = 'system/' + namespace
        destination = work / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise RuntimeError('Sampling preparation incomplete; review before retry')
        destination.write_text(sampling_dictionary(targets[:, :3], namespace))
        argv = ['postProcess', '-dict', name, '-fields', '(U p T)', '-time', stamp]
        write_once(dispatched, {'argv': argv})
        operation = exports.start(work, argv, kind='exec')
        write_once(binding, operation)
    while True:
        state = exports.status(operation['run_id'])
        if state['lifecycle'] != 'running':
            break
        time.sleep(.05)
    if state['lifecycle'] != 'completed' or not state['success']:
        raise RuntimeError('Native sampling failed/interrupted; inspect preserved sampling logs')
    directory, _ = exports.verify(operation['run_id'])
    result = {}
    for name in ('T', 'p', 'U'):
        folder = directory / 'artifacts/postProcessing' / (namespace + '_' + name)
        candidates = list(folder.glob('*/cloud_' + name + '.xy'))
        if len(candidates) != 1 or abs(float(candidates[0].parent.name) - float(stamp)) > 1e-8:
            raise RuntimeError('Expected native sample output missing or ambiguous: ' + name)
        raw = np.loadtxt(candidates[0], comments='#', ndmin=2)
        columns = 6 if name == 'U' else 4
        if raw.shape[1] != columns:
            raise RuntimeError('Unexpected raw sample columns for ' + name)
        values = raw[:, 3:] if name == 'U' else raw[:, 3]
        try:
            result[name] = align_samples(raw[:, :3], values, targets[:, :3])
        except ValueError as exc:
            raise InvalidNativeFields(str(exc)) from exc
    try:
        metrics = compare(targets, result, schema)
    except InvalidNativeSamples as exc:
        raise InvalidNativeFields(str(exc)) from exc
    metrics.update(sampling_operation=operation['run_id'], native_output_time=stamp,
                   grader_native_seconds=state['elapsed_seconds'])
    if not (output / 'metrics.json').exists():
        write_once(output / 'metrics.json', metrics)
    elif read(output / 'metrics.json') != metrics:
        raise RuntimeError('Stored sampling metrics differ from verified evidence')
    return metrics


def grade(task, runner, run_id, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    native, state = runner.verify(run_id)
    if state['kind'] != 'run':
        raise ValueError('A native run, not a preparation script, must be submitted')
    reference, policy = task.private()
    schema, _ = observations(task.root / 'public')
    if schema['csv_sha256'] != reference['public_csv_sha256']:
        raise ValueError('Public observations differ from frozen reference binding')
    binding = {'task': task.identity, 'run_id': run_id, 'artifacts': state['artifacts']}
    if (output / 'submission-binding.json').exists():
        if read(output / 'submission-binding.json') != binding:
            raise ValueError('Cannot reuse grading for another submission')
    else:
        write_once(output / 'submission-binding.json', binding)
    if (output / 'result.json').exists():
        value = read(output / 'result.json')
        if policy.get('release_status') == 'released':
            publish_reward(output, value, policy)
        return value
    if not state['success']:
        value = {'verdict': 'fail', 'reason': 'native_run_not_completed', 'reward': None}
    else:
        try:
            value = sample_case(native / 'artifacts', task.root / 'public', reference,
                                runner.sandbox, output / 'sampling')
            if policy.get('release_status') == 'released':
                from .dense_integrity import inspect
                from .dense_rubric import score
                try:
                    integrity = inspect(runner, run_id, reference)
                except Exception as exc:
                    # Valid sampled metrics survive an independent audit failure.
                    # Interrupted operations still propagate, never inventing a grade.
                    integrity = {'verdict': 'error', 'reasons': ['integrity_check_failed'],
                                 'detail': type(exc).__name__ + ': ' + str(exc)}
                value = score(value, policy['rubric'], integrity)
        except InvalidNativeFields as exc:
            value = {'verdict': 'fail', 'reason': 'native_observation_invalid', 'detail': str(exc), 'reward': None}
        except Exception as exc:
            value = {'verdict': 'error', 'reason': 'dense_sampling_infrastructure_error',
                     'detail': type(exc).__name__ + ': ' + str(exc), 'reward': None}
    if policy.get('release_status') == 'released':
        value.setdefault('grading_schema_version', 'dense-result-v2')
        value.setdefault('reward_version', policy['rubric']['version'])
        value.setdefault('metric_reward', None)
        value.setdefault('eligibility', 'error' if value['verdict'] == 'error' else 'invalid')
        if value['verdict'] == 'fail' and value.get('reward') is None:
            value['reward'] = 0.0
    write_once(output / 'result.json', value)
    if policy.get('release_status') == 'released':
        publish_reward(output, value, policy)
    return value


def publish_reward(output, value, policy):
    """Recover a missing reward projection without resampling or changing score."""
    reward = {'reward': value.get('reward'), 'verdict': value['verdict'],
              'reason': value['reason'], 'version': policy['rubric']['version'],
              'integrity_review_required': value.get('integrity_review_required', False)}
    # Old immutable projections keep their original schema on recovery.
    for key in ('metric_reward', 'eligibility', 'field_scores', 'grading_schema_version'):
        if key in value:
            reward[key] = value[key]
    path = Path(output) / 'reward.json'
    if path.exists():
        if read(path) != reward:
            raise RuntimeError('Reward differs from immutable grading result')
    else:
        write_once(path, reward)
