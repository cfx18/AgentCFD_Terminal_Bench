"""Classify native function objects by behavior, not by instance name.

Audited against OpenFOAM v2306 energyTransport, viscousDissipation and
runTimeControl sources in environments/docs-v2306/source. Unknown extensions
remain review items, not demonstrated violations. No GT configuration matching.
"""
from .physics.foam.parsed import Directive

MEASUREMENTS = {'sets', 'surfaces', 'probes', 'fieldMinMax', 'fieldAverage',
                'volFieldValue', 'surfaceFieldValue', 'residuals', 'solverInfo',
                'continuityError', 'yPlus', 'wallHeatFlux', 'writeCellCentres',
                'writeCellVolumes', 'CourantNo', 'time'}
LIBRARIES = {'sampling', 'fieldFunctionObjects', 'utilityFunctionObjects',
             'solverFunctionObjects', 'energyTransportFunctionObjects'}
CONDITIONS = {'minMax', 'average', 'equationInitialResidual', 'equationMaxIter',
              'minTimeStep', 'maxDuration', 'none'}


def _word(data, key, default=''):
    value = data.get(key, (default,))
    return value[0].strip('"') if isinstance(value, tuple) and len(value) == 1 else ''


def _hooks(value):
    """Reject runtime code/directives and nonstandard nested library loading."""
    if isinstance(value, Directive):
        return True
    if isinstance(value, dict):
        if 'libs' in value:
            libs = value['libs']
            if not isinstance(libs, tuple) or libs[:1] != ('(',) or libs[-1:] != (')',):
                return True
            for token in libs[1:-1]:
                name = token.strip('"')
                name = name.removeprefix('lib').removesuffix('.so')
                if name not in LIBRARIES:
                    return True
        kind = _word(value, 'type')
        if kind.startswith('coded') or kind in ('systemCall', 'exprField', 'expressionField'):
            return True
        return any(_hooks(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_hooks(child) for child in value)
    return isinstance(value, str) and (value.startswith(('$', '#')) or '#{' in value)


def classify(functions):
    """Return review reasons and explicit behavior evidence for the audit."""
    if not isinstance(functions, dict):
        return ['function_dictionary_requires_review'], []
    risks, evidence = [], []
    for name, function in functions.items():
        if not isinstance(function, dict) or _hooks(function):
            risks.append('function_runtime_hook_requires_review:' + name)
            continue
        kind = _word(function, 'type')
        role = None
        if kind in MEASUREMENTS:
            role = 'measurement'
        elif kind == 'energyTransport':
            # This solves an equation; viscousDissipation computes stress:grad(U),
            # not a target-value source. Other fvOptions need separate review.
            sources = function.get('fvOptions', {})
            valid = (isinstance(sources, dict)
                     and _word(function, 'field', 'T') == 'T'
                     and _word(function, 'phi', 'phi') == 'phi'
                     and _word(function, 'rho', 'rho') == 'rho')
            for source in sources.values() if isinstance(sources, dict) else ():
                if not isinstance(source, dict) or _word(source, 'type') != 'viscousDissipation':
                    valid = False
                    continue
                coeffs = source.get('viscousDissipationCoeffs', source)
                valid = valid and isinstance(coeffs, dict)
                if isinstance(coeffs, dict):
                    valid = (valid and coeffs.get('fields') == ('(', 'T', ')')
                             and _word(coeffs, 'U', 'U') == 'U'
                             and _word(coeffs, 'rho', 'rho') in ('rho', 'none'))
            if valid:
                role = 'physical_equation'
        elif kind == 'runTimeControl':
            # End-only control cannot prescribe a field. setTrigger can activate
            # other behavior and is intentionally not auto-cleared here.
            conditions = function.get('conditions', {})
            valid = (_word(function, 'satisfiedAction', 'end') == 'end'
                     and isinstance(conditions, dict) and bool(conditions))
            for condition in conditions.values() if isinstance(conditions, dict) else ():
                if not isinstance(condition, dict) or _word(condition, 'type') not in CONDITIONS:
                    valid = False
                    continue
                if _word(condition, 'type') in ('minMax', 'average'):
                    source = functions.get(_word(condition, 'functionObject'), {})
                    valid = (valid and isinstance(source, dict)
                             and _word(source, 'type') in MEASUREMENTS and not _hooks(source))
            if valid:
                role = 'stopping_control'
        if role is None:
            risks.append('function_behavior_requires_review:' + name)
        evidence.append({'name': name, 'type': kind, 'role': role or 'review'})
    return risks, evidence
