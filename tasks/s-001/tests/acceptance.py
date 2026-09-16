"""Independent extraction and quantitative acceptance; never execute model code."""
from decimal import Decimal
import math
import re

from agentcfd_bench.foam.dictionary import entries, viscosity_scalar
from agentcfd_bench.foam.normalize import normalize
from agentcfd_bench.identity import fingerprint
from agentcfd_bench.foam.inputs import validate_files
from agentcfd_bench.spec import METRICS, analytic_profile


def safety_inputs(files):
    validate_files(files)
    for name, text in files.items():
        if name.startswith('constant/polyMesh/'):
            raise ValueError('Supplied mesh forbidden; submit blockMeshDict')
        tokens = normalize(text)
        for token in tokens:
            if token[0] in ('word', 'quoted') and any(c in token[1] for c in ('#', '$')):
                raise ValueError('This pilot does not execute includes/macros/dynamic entries')
            literal = token[1].strip('\"\'') if token[0] in ('word', 'quoted') else ''
            if literal in ('libs', 'functionObjectLibs', 'code', 'codeExecute') or literal.startswith('coded'):
                raise ValueError('Custom code/libraries are not accepted')
        if any(t == ('word', 'format') and tokens[i+1:i+2] != normalize('ascii')
               for i, t in enumerate(tokens)):
            raise ValueError('Only ASCII dictionaries/fields supported')
    control = entries(files.get('system/controlDict', ''))
    if control.get(('functions',)) not in (None, normalize('{}')):
        raise ValueError('Function objects are not supported by this pilot')


def scalar(tokens):
    if len(tokens) != 1 or tokens[0][0] != 'number':
        raise ValueError('Expected one literal number')
    number = float(Decimal(tokens[0][1:]))
    if not math.isfinite(number):
        raise ValueError('Nonfinite number')
    return number


def disabled(tokens):
    """Literal OpenFOAM switch spellings; no substring matching or coercion.

    An absent option uses the runtime's false/uncompressed default. Unknown
    spellings are NOT treated as false just because OpenFOAM can warn/fallback.
    """
    words = ('false', 'off', 'no', '0', 'f', 'n', 'none')
    return tokens is None or tokens in tuple(normalize(word) for word in words)


def physics_contract(files):
    """Only PUBLIC physical constraints. Numerical choices are not reference-matched."""
    required = {
        'system/controlDict': {'application': 'icoFoam', 'startFrom': 'startTime', 'startTime': '0',
            'stopAt': 'endTime', 'endTime': '2', 'writeFormat': 'ascii'},
        '0/U': {'dimensions': '[0 1 -1 0 0 0 0]', 'internalField': 'uniform (0 0 0)',
            'boundaryField/top/type': 'fixedValue', 'boundaryField/top/value': 'uniform (1 0 0)',
            'boundaryField/bottom/type': 'fixedValue', 'boundaryField/bottom/value': 'uniform (0 0 0)'},
        '0/p': {'dimensions': '[0 2 -2 0 0 0 0]', 'internalField': 'uniform 0',
            'boundaryField/top/type': 'zeroGradient', 'boundaryField/bottom/type': 'zeroGradient'},
        'system/blockMeshDict': {
            'vertices': '((0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 0.1) (1 0 0.1) (1 1 0.1) (0 1 0.1))',
            'blocks': '(hex (0 1 2 3 4 5 6 7) (4 20 1) simpleGrading (1 1 1))'},
    }
    for field in ('0/U', '0/p'):
        for patch, kind in [('left', 'cyclic'), ('right', 'cyclic'), ('frontAndBack', 'empty')]:
            required[field]['boundaryField/' + patch + '/type'] = kind
    errors = []
    for name, constraints in required.items():
        tree = entries(files.get(name, ''))
        for path, expected in constraints.items():
            if (name == '0/U' and path.startswith('boundaryField/bottom/')
                    and tree.get(('boundaryField', 'bottom', 'type')) == normalize('noSlip')):
                continue
            if tree.get(tuple(path.split('/'))) != normalize(expected):
                errors.append(name + ':' + path)
        if name in ('0/U', '0/p'):
            patches = {p[1] for p in tree if p[:1] == ('boundaryField',) and len(p) >= 2}
            if patches != {'left', 'right', 'top', 'bottom', 'frontAndBack'}:
                errors.append(name + ':patch_set')
    mesh = entries(files.get('system/blockMeshDict', ''))
    # Both are optional in blockMesh. An omitted list is empty, not a defect.
    for key in ('edges', 'mergePatchPairs'):
        if mesh.get((key,)) not in (None, normalize('()')):
            errors.append('system/blockMeshDict:' + key)
    if {p[0] for p in mesh} - {'FoamFile', 'scale', 'convertToMeters', 'vertices', 'blocks',
                              'edges', 'boundary', 'mergePatchPairs'}:
        errors.append('system/blockMeshDict:unregistered_mesh_transform_or_option')
    scaling = [mesh[p] for p in (('scale',), ('convertToMeters',)) if p in mesh]
    # Default length scale is one. If both aliases are supplied, require both
    # to agree instead of guessing which implementation-specific one wins.
    if any(scalar(value) != 1 for value in scaling):
        errors.append('system/blockMeshDict:scale')
    # Patch list parsed as a dictionary, preserving physical faces but allowing order changes.
    boundary = mesh.get(('boundary',), ())
    if not boundary or boundary[0] != ('punctuation', '(') or boundary[-1] != ('punctuation', ')'):
        errors.append('system/blockMeshDict:boundary')
    else:
        from agentcfd_bench.fixture import MESH_BOUNDARY
        def token_text(token):
            return str(Decimal(token[1:])) if token[0] == 'number' else token[1]
        observed = entries(' '.join(token_text(t) for t in boundary[1:-1]))
        expected = entries(MESH_BOUNDARY)
        def semantic_boundary(tree):
            value = dict(tree)
            for path, tokens in tree.items():
                if path[-1] != 'faces':
                    continue
                if tokens[0] != ('punctuation', '(') or tokens[-1] != ('punctuation', ')'):
                    raise ValueError('Invalid face list')
                faces, current = [], None
                for token in tokens[1:-1]:
                    if token == ('punctuation', '(') and current is None:
                        current = []
                    elif token == ('punctuation', ')') and current is not None:
                        if len(current) != 4 or len(set(current)) != 4:
                            raise ValueError('Expected four unique face vertices')
                        faces.append(frozenset(current))
                        current = None
                    elif current is not None:
                        current.append(scalar((token,)))
                    else:
                        raise ValueError('Invalid face syntax')
                if current is not None or len(set(faces)) != len(faces):
                    raise ValueError('Duplicate or incomplete mesh face')
                value[path] = frozenset(faces)
            return value
        if semantic_boundary(observed) != semantic_boundary(expected):
            errors.append('system/blockMeshDict:boundary_faces_and_types')
    nu = viscosity_scalar(entries(files.get('constant/transportProperties', '')).get(('nu',), ()))
    if nu is None or scalar((nu,)) != 0.1:
        errors.append('constant/transportProperties:nu')
    control = entries(files.get('system/controlDict', ''))
    try:
        dt = scalar(control.get(('deltaT',), ()))
        if not 0 < dt <= 0.01:
            errors.append('system/controlDict:deltaT')
    except ValueError:
        errors.append('system/controlDict:deltaT')
    if not disabled(control.get(('adjustTimeStep',))):
        errors.append('system/controlDict:adjustTimeStep')
    if not disabled(control.get(('writeCompression',))):
        errors.append('system/controlDict:writeCompression')
    # Extra input names alone are not evidence of changed physics. icoFoam is
    # pinned by the executor (not selected by an agent's application string).
    # ALL submitted files still undergo safety_inputs and native acceptance.
    # Unlike passive dictionaries, phi is READ_IF_PRESENT: don't permit an
    # independent face flux to override the zero-velocity initial condition.
    if '0/phi' in files:
        errors.append('0/phi:submit_velocity_not_independent_face_flux')
    return {'passed': not errors, 'violations': errors}


def vectors(text, count=80):
    tree = entries(text)
    if tree.get(('FoamFile', 'class')) != normalize('volVectorField'):
        raise ValueError('Native U is not a volVectorField')
    if tree.get(('dimensions',)) != normalize('[0 1 -1 0 0 0 0]'):
        raise ValueError('Native U dimensions mismatch')
    tokens = tree.get(('internalField',), ())
    if tokens[:1] == normalize('uniform'):
        data = tokens[1:]
        if len(data) != 5 or data[0] != ('punctuation', '(') or data[-1] != ('punctuation', ')'):
            raise ValueError('Malformed uniform vector')
        return [[scalar((t,)) for t in data[1:4]]] * count
    if tokens[:2] != normalize('nonuniform List<vector>') or len(tokens) != 5 + count * 5:
        raise ValueError('Unsupported/nonuniform field size')
    if scalar(tokens[2:3]) != count or tokens[3] != ('punctuation', '(') or tokens[-1] != ('punctuation', ')'):
        raise ValueError('Wrong cell count')
    result = []
    for i in range(count):
        chunk = tokens[4 + 5*i:9 + 5*i]
        if chunk[0] != ('punctuation', '(') or chunk[-1] != ('punctuation', ')'):
            raise ValueError('Invalid vector list')
        result.append([scalar((t,)) for t in chunk[1:4]])
    return result


def extract(artifacts):
    field_names = [n for n in artifacts if re.fullmatch(r'[0-9.eE+\-]+/U', n)]
    if not field_names:
        raise ValueError('Missing native final field')
    name = max(field_names, key=lambda n: float(n.split('/')[0]))
    time_value = float(name.split('/')[0])
    if abs(time_value - 2) > 1e-8:
        raise ValueError('Final time coverage incomplete')
    u = vectors(artifacts[name])
    # Canonical single hex: x index varies fastest. Enforced by public mesh contract.
    profile = [sum(u[4*j+i][0] for i in range(4))/4 for j in range(20)]
    matches = re.findall(r'Solving for Ux, Initial residual = ([^,\s]+)', artifacts['solver.log'])
    if not matches:
        raise ValueError('Missing native Ux residual evidence')
    residual = float(matches[-1])
    if not math.isfinite(residual):
        raise ValueError('Nonfinite residual')
    values = {'ux_profile': profile, 'uy_rms': math.sqrt(sum(v[1]**2 for v in u)/80),
              'final_time': time_value, 'ux_final_initial_residual': residual}
    return {name: {'unit': METRICS[name][0], 'value': value} for name, value in values.items()}


def parse_action(files):
    from agentcfd_bench.spec import ACTION_FILE, loads
    obj = loads(files.get(ACTION_FILE, ''))
    if not isinstance(obj, dict):
        raise ValueError('Expected action object')
    if obj.get('action') == 'run' and obj == {'action': 'run', 'solver': 'icoFoam'}:
        return obj
    if obj.get('action') != 'report' or set(obj) != {'action', 'run_id', 'measurements'}:
        raise ValueError('Expected run or report action; no free-form fallback guessing')
    if not re.fullmatch(r'r-[0-9]{6}', str(obj['run_id'])):
        raise ValueError('Invalid run ID')
    validate_measurements(obj['measurements'])
    return obj


def validate_measurements(measures):
    """Also enforced at the library evaluate boundary, not only by the CLI."""
    if not isinstance(measures, dict) or set(measures) != set(METRICS):
        raise ValueError('All four requested measurement names required')
    for name, (unit, size) in METRICS.items():
        measure = measures[name]
        if not isinstance(measure, dict) or set(measure) != {'unit', 'value'} or measure['unit'] != unit:
            raise ValueError('Measurement shape/unit mismatch: ' + name)
        value = measure['value']
        values = value if isinstance(value, list) else [value]
        if (len(values) != size or (size == 1 and isinstance(value, list))
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
            raise ValueError('Finite, correctly-sized numeric measurement required: ' + name)


def evaluate(action, frozen_run):
    validate_measurements(action['measurements'])
    if frozen_run['verdict'] != 'pass':
        return {'verdict': 'fail', 'reason': 'run_not_completed', 'checks': {}}
    artifacts = frozen_run['artifacts']
    if fingerprint(artifacts) != frozen_run['artifact_hash']:
        raise RuntimeError('Artifact integrity mismatch; infrastructure evidence compromised')
    observed = extract(artifacts)
    mismatch = []
    for name, measurement in observed.items():
        left, right = action['measurements'][name]['value'], measurement['value']
        a, b = (left, right) if isinstance(right, list) else ([left], [right])
        if any(abs(x-y) > 1e-6 + 1e-5*abs(y) for x, y in zip(a, b)):
            mismatch.append(name)
    physical_error = max(abs(x-y) for x, y in zip(observed['ux_profile']['value'], analytic_profile()))
    checks = {'task_contract': frozen_run['contract']['passed'], 'report_matches_artifacts': not mismatch,
              'velocity_profile': physical_error <= 0.005, 'transverse_velocity': observed['uy_rms']['value'] <= 1e-6,
              'final_time': abs(observed['final_time']['value']-2) <= 1e-8}
    return {'verdict': 'pass' if all(checks.values()) else 'fail', 'checks': checks,
            'reason': 'quantitative_acceptance' if all(checks.values()) else 'acceptance_failed',
            'report_mismatch': mismatch, 'independent_measurements': observed,
            'private_profile_max_error': physical_error}
