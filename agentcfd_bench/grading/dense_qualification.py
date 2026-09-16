"""Release evidence bound to code, public inputs, user rubric and native replay."""
from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET

from .dense_rubric import approved_rubric
from ..execution.files import inventory
from ..records.store import digest, read


def code_identity():
    root = Path(__file__).resolve().parents[1]
    files = inventory(root)
    return digest({k:v for k,v in files.items() if k.endswith('.py') and (
        k.startswith(('grading/dense', 'grading/physics/', 'execution/')) or k == 'records/store.py')})


def tests_summary(path):
    try:
        cases = ET.parse(path).getroot().findall('.//testcase')
    except ET.ParseError as exc:
        raise ValueError('Invalid qualification test evidence') from exc
    required = {'test_plain_provenance_passes', 'test_copied_target_temperature_as_initial_state_fails',
                'test_code_hook_is_review_not_physics_failure', 'test_reward_recovery_never_regrades_or_changes_result',
                'test_frozen_solver_input_survives_native_writes', 'test_unknown_sampler_dispatch_is_not_reissued'}
    names = {row.get('name','').split('[')[0] for row in cases}
    if not required <= names or not cases or any(list(row) and any(
            row.find(name) is not None for name in ('failure','error','skipped')) for row in cases):
        raise ValueError('Dense release tests missing, failed or skipped')
    if sum(row.get('name','').startswith('test_real_sampling_changed_mesh_boundary_names_and_binary[') for row in cases) != 3:
        raise ValueError('Real cross-mesh/binary sampling qualification missing')
    return {'total':len(cases), 'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def validate(task, reference, policy):
    proof = read(task.root / 'private/qualification.json')
    replay = read(task.root / 'private/native-replay.json')
    expected_initial = {'U':[0,0,0], 'T':300 if task.task_id == 's-203' else 293,
                        'p':0 if task.task_id == 's-203' else 100000}
    if policy['rubric'] != approved_rubric(task.task_id) or reference.get('initial_state') != expected_initial:
        raise ValueError('Released rubric or physical initialization differs from approval')
    if read(task.root / 'public/rubric.json') != policy['rubric']:
        raise ValueError('Public/private reward protocol differs')
    if (proof['code_identity'] != code_identity() or proof['reference_identity'] != digest(reference)
            or proof['policy_identity'] != digest(policy)
            or proof['public_identity'] != digest(inventory(task.root / 'public'))
            or proof['tests'] != tests_summary(task.root / 'private/qualification-tests.xml')
            or proof['replay_identity'] != digest(replay)):
        raise ValueError('Dense qualification evidence stale or changed')
    if replay['coverage'] != 1 or replay['metric_status'] != 'completed' or any(
            row['maximum_absolute_error'] > 1e-8 for row in replay['metrics'].values()):
        raise ValueError('Dense reference native replay failed')
