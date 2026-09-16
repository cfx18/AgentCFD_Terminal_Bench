"""Regressions from the two submitted web-enabled reconstruction trials."""
import json
import shutil

import pytest

from agentcfd_bench.execution.files import inventory
from agentcfd_bench.grading.dense_functions import classify
from agentcfd_bench.grading.dense_integrity import inspect
from agentcfd_bench.grading.physics.foam.parsed import read as parse
from agentcfd_bench.grading.physics.foam.science_metrics import field_values
from agentcfd_bench.records.store import read, write_once
from test_dense_release import native_fixture, measurement


def test_input_location_optional_but_output_location_still_required(tmp_path):
    runner, native, reference = native_fixture(tmp_path)
    for name in ('U', 'T', 'p'):
        path = native / 'inputs/0' / name
        text = path.read_text().replace('location "0";', '')
        path.write_text(text)
        with pytest.raises(ValueError, match='location mismatch'):
            field_values(text, name, 1, reference['dimensions'][name], 0)
    assert inspect(runner, native.name, reference)['verdict'] == 'pass'


@pytest.mark.parametrize('old,new,verdict', [
    ('location "0";', 'location "1";', 'review'),
    ('[0 0 0 1 0 0 0]', '[0 1 0 0 0 0 0]', 'review'),
    ('uniform 300;', 'uniform 315;', 'fail'),
])
def test_optional_location_does_not_relax_other_input_checks(tmp_path, old, new, verdict):
    runner, native, reference = native_fixture(tmp_path)
    path = native / 'inputs/0/T'
    path.write_text(path.read_text().replace(old, new))
    assert inspect(runner, native.name, reference)['verdict'] == verdict


ENERGY = '''anyName {type energyTransport; libs ("libsolverFunctionObjects.so"); field T;
    rhoInf 1.2; Cp 1000; kappa .0257;
    fvOptions {heat {type viscousDissipation; fields (T); rhoInf rho [1 -3 0 0 0 0 0] 1.2;}}}'''
STOPPING = '''mean {type volFieldValue; libs (fieldFunctionObjects); operation volAverage; fields (p);}
    stop {type runTimeControl; libs (utilityFunctionObjects); satisfiedAction end;
    conditions {enough {type minMax; functionObject mean; fields ("volAverage(p)");
    mode maximum; value 101601.8871;}}}'''


@pytest.mark.parametrize('text,role', [(ENERGY, 'physical_equation'), (STOPPING, 'stopping_control')])
def test_native_physics_and_stopping_are_not_target_injection(text, role):
    risks, evidence = classify(parse(text))
    assert risks == []
    assert role in {r['role'] for r in evidence}


@pytest.mark.parametrize('text', [ENERGY, STOPPING])
def test_native_function_classification_integrates_with_provenance(tmp_path, text):
    runner, native, reference = native_fixture(tmp_path, control_extra='functions {' + text + '}')
    result = inspect(runner, native.name, reference)
    assert result['verdict'] == 'pass' and result['functions']


@pytest.mark.parametrize('text', [
    ENERGY.replace('viscousDissipation;', 'scalarSemiImplicitSource;'),
    ENERGY.replace('viscousDissipation;', 'codedSource;'),
    ENERGY.replace('libsolverFunctionObjects.so', '/workspace/libsolverFunctionObjects.so'),
    ENERGY.replace('field T;', 'field copiedTarget;'),
    ENERGY.replace('fields (T);', 'fields (T); #include "target"\n'),
    STOPPING.replace('satisfiedAction end;', 'satisfiedAction setTrigger; trigger 1;'),
    STOPPING.replace('functionObject mean;', 'functionObject target;'),
    STOPPING.replace('type minMax;', 'type customCondition;'),
])
def test_unknown_sources_hooks_and_trigger_actions_stay_review(text):
    assert classify(parse(text))[0]


def restart_chain(tmp_path, *, producer_sequence=1, child_sequence=2):
    runner, parent, reference = native_fixture(tmp_path)
    # Producer ID deliberately sorts AFTER its child and future copy.
    actual = tmp_path / 'r-ffffffffffffffff'; parent.rename(actual); parent = actual
    (parent / 'dispatch.json').write_text(json.dumps({'sequence': producer_sequence}))
    (parent / 'stdout.log').write_text('Time = 0.5\nSolving for Ux\nEnd\n')
    child = tmp_path / 'r-2222222222222222'
    shutil.copytree(parent / 'inputs', child / 'inputs')
    (child / 'inputs/0.5').mkdir()
    for field in ('U', 'T', 'p'):
        (child / 'inputs/0.5' / field).write_text('native fixture ' + field)
    (child / 'inputs/system/controlDict').write_text('startFrom latestTime; startTime 0;')
    hashes = inventory(child / 'inputs')
    write_once(child / 'spec.json', {**read(parent / 'spec.json'), 'inputs': hashes})
    write_once(child / 'dispatch.json', {'sequence': child_sequence})
    (child / 'stdout.log').write_text('Time = 1.5\nSolving for Ux\nEnd\n')
    write_once(parent / 'result.json', {'kind': 'run', 'success': True,
        'artifacts': {k: v for k, v in hashes.items() if k.startswith('0.5/')}})
    return runner, parent, child, reference


def test_random_uuid_and_future_copies_cannot_reverse_restart_ancestry(tmp_path):
    runner, parent, child, reference = restart_chain(tmp_path)
    future = tmp_path / 'r-0000000000000000'
    shutil.copytree(child, future)
    (future / 'dispatch.json').write_text(json.dumps({'sequence': 3}))
    shutil.copy(parent / 'result.json', future / 'result.json')
    result = inspect(runner, child.name, reference)
    assert result['verdict'] == 'pass' and result['parent'] == parent.name
    assert result['restart_evidence']['parent_sequence'] == 1
    assert result['ancestor']['start'] == 0


@pytest.mark.parametrize('fault', ['future', 'missing_order', 'changed_field', 'uncomputed_time'])
def test_restart_requires_prior_computation_and_exact_field_evidence(tmp_path, fault):
    runner, parent, child, reference = restart_chain(tmp_path)
    if fault == 'future':
        (parent / 'dispatch.json').write_text(json.dumps({'sequence': 3}))
    elif fault == 'missing_order':
        (child / 'dispatch.json').unlink()
    elif fault == 'changed_field':
        spec = read(child / 'spec.json'); spec['inputs']['0.5/U'] = 'different'
        (child / 'spec.json').write_text(json.dumps(spec))
    else:
        (parent / 'stdout.log').write_text('Time = 0.1\nSolving for Ux\nEnd\n')
    assert inspect(runner, child.name, reference)['verdict'] == 'review'


def test_restart_still_verifies_the_parent_receipt(tmp_path):
    runner, parent, child, reference = restart_chain(tmp_path)
    previous = runner.verify
    def verify(run_id):
        if run_id == parent.name:
            raise RuntimeError('Artifact hash mismatch')
        return previous(run_id)
    runner.verify = verify
    with pytest.raises(RuntimeError, match='hash mismatch'):
        inspect(runner, child.name, reference)


def test_restart_cycle_cannot_become_a_pass(tmp_path):
    runner, parent, child, reference = restart_chain(tmp_path)
    result = inspect(runner, child.name, reference, visited={child.name})
    assert result['verdict'] == 'review' and result['reasons'] == ['restart_provenance_cycle']


def test_integrity_failure_preserves_independently_sampled_metric_score(tmp_path, monkeypatch):
    from test_dense_release import ROOT
    from agentcfd_bench.tasks.loader import Task
    from agentcfd_bench.grading import dense_native, dense_integrity
    from agentcfd_bench.grading.dense_rubric import approved_rubric
    from types import SimpleNamespace
    target = tmp_path / 'task'
    shutil.copytree(ROOT / 'task-drafts/dense-observation-v1/s-203', target)
    policy = read(target / 'private/grading.json')
    policy.update(release_status='released', rubric=approved_rubric('s-203'))
    (target / 'private/grading.json').write_text(json.dumps(policy))
    native = tmp_path / 'native'; (native / 'artifacts').mkdir(parents=True)
    runner = SimpleNamespace(verify=lambda _: (native, {'kind':'run','success':True,'artifacts':{}}), sandbox=None)
    monkeypatch.setattr(dense_native, 'sample_case', lambda *a: measurement(.175, .2))
    def broken(*args):
        raise RuntimeError('Missing parent receipt')
    monkeypatch.setattr(dense_integrity, 'inspect', broken)
    output = tmp_path / 'grading'
    value = dense_native.grade(Task.load(target), runner, 'r-one', output)
    assert value['metric_reward'] == pytest.approx(.5)
    assert value['reward'] is None and value['eligibility'] == 'error' and value['verdict'] == 'error'
    assert read(output / 'reward.json')['metric_reward'] == pytest.approx(.5)


def test_report_separates_accuracy_eligibility_and_official_score(tmp_path):
    from agentcfd_bench.records.store import Store
    from agentcfd_bench.reports.summary import report, markdown
    for task, eligibility, verdict, reward in [('a', 'eligible', 'fail', .8),
            ('b', 'invalid', 'fail', 0), ('c', 'review', 'not_evaluated', None),
            ('d', 'error', 'error', None)]:
        trial = tmp_path / 'trials' / task
        Store(trial).set('trial', {'lifecycle': 'completed', 'verdict': verdict})
        write_once(trial / 'grading/result.json', {'verdict': verdict, 'reward': reward,
            'eligibility': eligibility, 'metric_reward': .8,
            'integrity_review_required': eligibility == 'review'})
    result = report(tmp_path)
    assert result['reward_denominator'] == 2 and result['mean_reward_scored'] == .4
    assert result['metric_reward_count'] == 4 and result['mean_metric_reward_diagnostic'] == .8
    assert result['eligibility_counts'] == {'eligible': 1, 'invalid': 1, 'review': 1, 'error': 1, 'unknown': 0}
    assert report(tmp_path) == result
    assert '物理匹配分' in markdown(tmp_path) and '正式 reward' in markdown(tmp_path)


def test_regrade_identity_includes_dense_rubric_and_integrity_code(monkeypatch):
    from agentcfd_bench.grading import qualification
    files = {'dense_rubric.py': 'old', 'dense_integrity.py': 'old', 'dense_functions.py': 'old'}
    monkeypatch.setattr(qualification, 'inventory', lambda _: files)
    identities = [qualification.grader_identity()]
    for name in files:
        files[name] = 'new'
        identities.append(qualification.grader_identity())
    assert len(set(identities)) == 4
