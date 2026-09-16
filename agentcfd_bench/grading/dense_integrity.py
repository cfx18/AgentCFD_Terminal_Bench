"""Audit observable solver provenance. Ambiguous implementations go to review.

This does not claim to prove intent or rule out every adversarial program. It
rejects demonstrated fabricated starts and flags executable field/control hooks,
instead of confusing a potentially legitimate implementation with a wrong answer.
"""
import gzip
from pathlib import Path
import re

import numpy as np

from .physics.foam.parsed import read as parse, Directive
from .physics.foam.science_metrics import field_values
from ..records.store import read
from .dense_functions import classify

VERSION = 'dense-integrity-v2'
TIME = re.compile(r'^Time = ([0-9.eE+\-]+)\s*$', re.M)


def _text(path):
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='ascii') as stream:
            return stream.read()
    return path.read_text(encoding='ascii')


def _directives(value):
    if isinstance(value, Directive):
        return True
    if isinstance(value, dict):
        return any(_directives(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return any(_directives(v) for v in value)
    return False


def inspect(runner, run_id, reference, *, visited=None, require_endpoint=True):
    """Use immutable input/output receipts, including verified restart ancestry."""
    visited = set() if visited is None else set(visited)
    if run_id in visited:
        return _result('review', ['restart_provenance_cycle'])
    visited.add(run_id)
    native, state = runner.verify(run_id)
    spec = read(native / 'spec.json')
    if not spec.get('input_evidence'):
        return _result('review', ['immutable_input_snapshot_missing'])
    work = native / 'inputs'
    argv = spec['argv']
    if any(flag in argv for flag in ('-postProcess', '-help', '-help-full', '-doc', '-srcDoc')):
        return _result('fail', ['submitted_operation_is_not_a_calculation'])
    log = (native / 'stdout.log').read_text(errors='replace')
    times = [float(n) for n in TIME.findall(log)]
    if not times or max(times) <= 0:
        return _result('fail', ['no_native_time_or_iteration_advance'])
    risks = []
    program = Path(runner.sandbox.foam_root) / 'bin' / Path(argv[0]).name
    with program.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            risks.append('native_wrapper_requires_review')
    if not re.search(r'Solving for (?:U[xyz]?|p(?:_rgh)?|T|h|e)\b', log):
        risks.append('unrecognized_equation_solve_evidence')
    if any(flag in argv for flag in ('-case', '-region', '-dict', '-lib')):
        risks.append('nondefault_case_or_region_requires_review')
    try:
        control = parse(_text(work / 'system/controlDict'))
        if _directives(control):
            risks.append('control_directives_require_review')
        function_risks, functions = classify(control.get('functions', {}))
        risks.extend(function_risks)
        if control.get('libs'):
            risks.append('additional_runtime_libraries')
        start_from = control.get('startFrom', ('startTime',))[0]
        numeric = sorted(float(p.name) for p in work.iterdir()
                         if p.is_dir() and re.fullmatch(r'[0-9]+(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?', p.name))
        if start_from == 'latestTime':
            start = max(numeric)
        elif start_from == 'firstTime':
            start = min(numeric)
        elif start_from == 'startTime':
            start = float(control.get('startTime', ('0',))[0])
        else:
            raise ValueError('Unknown startFrom')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError, UnicodeError):
        return _result('review', [*risks, 'initialization_not_statically_resolved'])
    if max(times) <= start:
        return _result('fail', ['no_evolution_after_loaded_state'])
    if require_endpoint and reference['endpoint_kind'] == 'physical_time' and max(times) < reference['required_time'] - 1e-8:
        return _result('fail', ['required_physical_time_not_computed'])
    # Runtime expressions/source terms are not blanket-rejected, but cannot earn
    # automatic reward without reviewing whether they prescribe the target.
    for path in work.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(work).as_posix()
        active = (rel.startswith(('0/', 'constant/')) and '/polyMesh/' not in rel) or rel in (
            'system/fvSchemes', 'system/fvSolution')
        if path.suffix == '.so' or (active and 'fvOptions' in path.name):
            risks.append('runtime_extension_or_source:' + rel)
        if active:
            try:
                text = _text(path)
                if '#{' in text or re.search(r'\b(?:coded\w*|exprField|expressionField|systemCall)\b', text):
                    risks.append('executable_field_hook:' + rel)
                if re.search(r'#(?:include|code|eval|calc)|\blibs\s*\(', text):
                    risks.append('runtime_directive:' + rel)
            except (UnicodeError, OSError):
                pass  # Binary field data are checked below, not called cheating.
    if start > 0:
        prefixes = [p.name + '/' for p in work.iterdir() if p.is_dir()
                    and re.fullmatch(r'[0-9]+(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?', p.name)
                    and abs(float(p.name) - start) < 1e-9]
        loaded = {name: sha for name, sha in spec['inputs'].items()
                  if any(name.startswith(prefix) for prefix in prefixes) or '/polyMesh/' in name}
        dispatch_path = native / 'dispatch.json'
        sequence = read(dispatch_path).get('sequence') if dispatch_path.exists() else None
        if type(sequence) is not int or sequence <= 0:
            return _result('review', [*risks, 'restart_dispatch_order_missing'], functions=functions)
        parents = []
        for path in runner.root.glob('r-*/result.json'):
            if path.parent.name in visited:
                continue
            dispatch = path.parent / 'dispatch.json'
            prior = read(dispatch).get('sequence') if dispatch.exists() else None
            if type(prior) is not int or not 0 < prior < sequence:
                continue  # A later run cannot be the source of earlier inputs.
            parent = read(path)
            if parent.get('kind') == 'run' and parent.get('success') and loaded and all(
                    parent['artifacts'].get(name) == sha for name, sha in loaded.items()):
                # Do not select a run that merely carried a copied time folder.
                log = (path.parent / 'stdout.log').read_text(errors='replace')
                if any(abs(float(t) - start) < 1e-8 for t in TIME.findall(log)):
                    parents.append((prior, path.parent.name))
        if not parents:
            return _result('review', [*risks, 'restart_not_bound_to_prior_native_fields'],
                           functions=functions, start=start)
        # Earliest actual producer, never random UUID ordering or a future copy.
        parent_id = min(parents)[1]
        parent = inspect(runner, parent_id, reference, visited=visited, require_endpoint=False)
        if parent['verdict'] != 'pass':
            return _result(parent['verdict'], [*risks, 'ancestor:' + parent['verdict'], *parent['reasons']],
                           parent=parent_id, start=start, ancestor=parent, functions=functions)
        return _result('review' if risks else 'pass', risks, parent=parent_id, start=start,
                       ancestor=parent, functions=functions, restart_evidence={
                           'parent_sequence': min(parents)[0], 'sequence': sequence,
                           'matched_input_files': len(loaded),
                           'method': 'exact_snapshot_hashes_and_native_time_with_prior_dispatch'})
    for name, expected in reference['initial_state'].items():
        paths = [p for p in (work / '0' / name, work / '0' / (name + '.gz')) if p.is_file()]
        if len(paths) != 1:
            risks.append('initial_field_requires_review:' + name)
            continue
        try:
            text = _text(paths[0]); tree = parse(text)
            if _directives(tree):
                risks.append('initial_field_directive:' + name)
                continue
            if tree['FoamFile'].get('format') == ('binary',):
                if tree['internalField'][:1] != ('uniform',):
                    raise ValueError('Nonuniform binary start needs native review')
                text = re.sub(r'\bformat\s+binary\s*;', 'format ascii;', text, count=1)
            value = tree['internalField']
            count = 1 if value[0] == 'uniform' else int(value[2])
            values = np.asarray(field_values(text, name, count, reference['dimensions'][name], 0,
                                             allow_missing_location=True))
            if not np.allclose(values, expected, rtol=0, atol=1e-8):
                return _result('fail', ['prescribed_initial_state_not_used:' + name])
        except (ValueError, KeyError, TypeError, IndexError, UnicodeError):
            risks.append('initial_field_representation_requires_review:' + name)
    return _result('review' if risks else 'pass', risks, start=start, functions=functions)


def _result(verdict, reasons, **evidence):
    return {'version': VERSION, 'verdict': verdict, 'reasons': sorted(set(reasons)),
            'claim': 'observable_provenance_checks_not_proof_against_all_adversarial_programs', **evidence}
