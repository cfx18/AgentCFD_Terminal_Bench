"""Freeze a diverse tutorial authoring queue, without silently dropping sources."""
import argparse
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from .prepare import native_prompt
from ..grading.physics.foam.parsed import read as dictionary
from ..records.store import read, write_once

FAMILIES = ('incompressible', 'heatTransfer', 'compressible', 'basic', 'multiphase',
            'combustion', 'lagrangian', 'stressAnalysis', 'DNS', 'electromagnetics',
            'verificationAndValidation', 'discreteMethods')


def inspect_source(row, source_root, foam_root):
    path = row['source_path']
    prefix = 'OpenFOAM-v2306/tutorials/'
    if not path.startswith(prefix):
        return {'screening': 'needs_support', 'reason': 'extension_module_workflow'}
    family = path[len(prefix):].split('/')[0]
    if family not in FAMILIES:
        return {'screening': 'out_of_scope', 'reason': 'not_a_physical_solver_tutorial', 'family': family}
    control = Path(source_root) / path / 'system/controlDict'
    if not control.is_file():
        return {'screening': 'needs_support', 'reason': 'missing_local_control_dictionary', 'family': family}
    try:
        app = dictionary(control.read_text()).get('application')
    except (ValueError, UnicodeError, RuntimeError) as exc:
        return {'screening': 'needs_review', 'reason': 'control_dictionary_not_statically_resolved',
                'error_type': type(exc).__name__, 'family': family}
    if not isinstance(app, tuple) or len(app) != 1 or not isinstance(app[0], str):
        return {'screening': 'needs_review', 'reason': 'application_not_statically_resolved', 'family': family}
    app = app[0]
    if not app or '/' in app or app.startswith('.') or not (Path(foam_root) / 'bin' / app).is_file():
        return {'screening': 'needs_support', 'reason': 'application_not_installed', 'application': app, 'family': family}
    return {'screening': 'candidate', 'family': family, 'application': app,
            'note': 'Availability only; no assertion of runnable workflow or valid physics.'}


def select(rows, limit, excluded=()):
    if type(limit) is not int or limit <= 0:
        raise ValueError('Positive author-attempt count required')
    buckets = defaultdict(deque)
    for row in sorted(rows, key=lambda r: (r['application'] if 'application' in r else '', r['source_path'])):
        if row['screening'] == 'candidate' and row['candidate_id'] not in excluded:
            buckets[row['family']].append(row)
    result = []
    while len(result) < limit and any(buckets.values()):
        for family in FAMILIES:
            if buckets[family] and len(result) < limit:
                result.append(buckets[family].popleft())
    return result


def freeze(pilot_config, output, limit=100, parallel=10, after_current=True):
    pilot_config, output = Path(pilot_config), Path(output).resolve()
    config = read(pilot_config)
    if output.exists():
        raise FileExistsError('Do not overwrite a campaign')
    registry = read(Path(config['root']) / 'registry.json')
    rows = [{**row, **inspect_source(row, Path(config['public']) / 'source', config['sandbox']['foam_root'])}
            for row in registry['candidates']]
    pilot_ids = [job for job in config['jobs'] if job != 'library']
    selected = select(rows, limit, excluded=pilot_ids)
    output.mkdir(parents=True)
    jobs = {}
    for row in selected:
        path = output / 'prompts' / (row['candidate_id'] + '.md')
        path.parent.mkdir(exist_ok=True)
        path.write_text(native_prompt(row))
        jobs[row['candidate_id']] = {'prompt': str(path), 'candidate': row,
                                     'expected_outputs': ['author-result.json', 'REVIEW.zh.md']}
    config = {**config, 'root': str(output), 'jobs': jobs, 'job_order': list(jobs), 'author_concurrency': parallel,
              'parent_campaign': str(pilot_config.resolve()), 'selection': 'family_round_robin_before_results',
              'attempt_count': len(jobs), 'target_qualified_tasks': 100}
    if after_current:
        config['after_campaign'] = str(pilot_config.resolve())
    write_once(output / 'registry.json', {**registry, 'candidates': rows,
        'created': datetime.now(timezone.utc).isoformat(), 'selection': list(jobs),
        'prior_pilot_ids': pilot_ids, 'screening_counts': dict(Counter(r['screening'] for r in rows)),
        'attempts_not_guaranteed_qualified_tasks': True})
    write_once(output / 'campaign.json', config)
    return {'root': str(output), 'registered': len(rows), 'selected_attempts': len(jobs),
            'families': dict(Counter(r['family'] for r in selected)), 'started': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--attempts', type=int, default=100)
    parser.add_argument('--parallel', type=int, default=10)
    args = parser.parse_args()
    print(__import__('json').dumps(freeze(args.pilot_config, args.output, args.attempts, args.parallel), ensure_ascii=False, indent=2))
