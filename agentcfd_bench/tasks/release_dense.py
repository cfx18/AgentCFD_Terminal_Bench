"""Publish a new dense task version only from passing local qualification evidence.

This command calls no model and never modifies the draft or historical reference.
"""
import argparse
from pathlib import Path
import shutil
import uuid

from ..grading.dense_qualification import code_identity, tests_summary, validate
from ..grading.dense_rubric import approved_rubric
from ..grading.dense_integrity import VERSION as INTEGRITY_VERSION
from ..execution.files import inventory
from ..records.store import read, write_once, digest
from .loader import Task


def release(draft, destination, tests, replay):
    draft, destination, tests, replay = map(Path, (draft, destination, tests, replay))
    evidence = tests_summary(tests)
    replay_rows = {r['task']:r for r in read(replay)['references']}
    if set(replay_rows) != {'s-203','s-204'}:
        raise ValueError('Both selected reference replays are required')
    for row in replay_rows.values():
        if row['coverage'] != 1 or any(m['maximum_absolute_error'] > 1e-8 for m in row['metrics'].values()):
            raise ValueError('Reference replay is not exact')
    if destination.exists():
        raise FileExistsError('Publish a new version, never overwrite a release')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / ('.dense-build-' + uuid.uuid4().hex)
    staging.mkdir()
    for task_id in ('s-203','s-204'):
        source = Task.load(draft / task_id)
        reference, _ = source.private()
        target = staging / task_id
        shutil.copytree(source.root / 'public', target / 'public')
        meta = read(source.root / 'task.json')
        meta.update(release_status='released', version=destination.name)
        write_once(target / 'task.json', meta)
        reference['initial_state'] = {'U':[0,0,0], 'T':300 if task_id == 's-203' else 293,
                                      'p':0 if task_id == 's-203' else 100000}
        rubric = approved_rubric(task_id)
        policy = {'policy':'dense-observation-v1', 'release_status':'released',
                  'rubric_approved':True, 'general_mesh_qualified':True, 'rubric':rubric,
                  'convergence_rules':[], 'integrity_policy':INTEGRITY_VERSION,
                  'qualification_scope':'single-fluid native U/T/p; physical-coordinate containing-cell sampling',
                  'unresolved_integrity':'human_review_no_reward_not_model_failure'}
        write_once(target / 'private/reference.json', reference)
        write_once(target / 'private/grading.json', policy)
        write_once(target / 'public/rubric.json', rubric)
        # Generated versioned release files; draft remains unchanged.
        obs = target / 'public/observations.md'
        content = obs.read_text().split('This draft reports raw metrics only.')[0]
        content += '''## Frozen scoring rule

The full scoring rule is in `/input/rubric.json`. For each of U, T and p, a normalized
RMSE at or below 0.05 and a normalized maximum error at or below 0.20 earn full
credit. RMSE at or above 0.30 or maximum error at or above 1.0 earns zero credit.
Between these anchors credit decreases linearly. The overall reward is the minimum
over both metrics and all three fields: a poor field cannot be hidden by averaging.
`pass` means full credit; intermediate reward is retained even when below full credit.
These are reconstruction tolerances, not a convergence certificate.

'''
        content += ('For this task only, remove the volume-weighted constant pressure discrepancy before scoring pressure shape. The raw bias is still recorded.\n'
                    if task_id == 's-203' else 'Absolute pressure is scored without any offset correction.\n')
        content += '''
The evaluator independently samples frozen native outputs. A copied field plus a
postprocessing-only command is not a calculation. Inputs are retained to audit
the stated initial condition and provenance of restarts. Custom executable field
hooks or unresolved restart provenance require human review rather than an
automatic physics failure or automatic reward. Ordinary meshing and diagnostics
are available; this is not a hidden configuration-template match.

Public observations may be used for your own comparisons. Submit one chosen
native calculation; the authoritative evaluator is not an iterative tuning tool.
'''
        obs.write_text(content)
        schema_path = target / 'public/observations/schema.json'
        schema = read(schema_path)
        schema['scoring_status'] = 'released; dense-reconstruction-reward-v1'
        import json
        schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + '\n')
        write_once(target / 'private/native-replay.json', replay_rows[task_id])
        shutil.copyfile(tests, target / 'private/qualification-tests.xml')
        write_once(target / 'private/qualification.json', {
            'code_identity':code_identity(), 'reference_identity':digest(reference),
            'policy_identity':digest(policy), 'public_identity':digest(inventory(target / 'public')),
            'tests':evidence, 'replay_identity':digest(replay_rows[task_id]),
            'source_replay':str(replay.resolve()),
            'limits':'No claim of unique mechanism identification or universal adversarial-proof execution',
        })
        task = Task.load(target)
        validate(task, reference, policy)
    staging.rename(destination)
    return {'release':str(destination.resolve()), 'tasks':['s-203','s-204'], 'tests':evidence, 'paid_calls':0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('draft','destination','tests','replay'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(release(args.draft, args.destination, args.tests, args.replay))
