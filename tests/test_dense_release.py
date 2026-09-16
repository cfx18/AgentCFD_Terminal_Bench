"""Approved reward, provenance abstention, and immutable reward recovery."""
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentcfd_bench.grading.dense_rubric import approved_rubric, score
from agentcfd_bench.grading.dense_integrity import inspect
from agentcfd_bench.grading.dense_native import publish_reward
from agentcfd_bench.execution.files import inventory
from agentcfd_bench.records.store import read, write_once

ROOT = Path(__file__).resolve().parents[1]


def measurement(rmse=0, maximum=0):
    return {'metric_status': 'completed', 'coverage': 1, 'metrics': {
        f: {'normalized_rmse': rmse, 'normalized_maximum_error': maximum,
            'normalizer': 1, 'gauge_aligned_rmse': rmse, 'gauge_aligned_maximum_error': maximum}
        for f in ('U', 'T', 'p')}}


@pytest.mark.parametrize('rmse,maximum,reward', [(0,0,1),(.05,.2,1),(.30,0,0),(0,1,0),(.175,.2,.5),(.05,.6,.5)])
def test_approved_reward_anchors_and_interpolation(rmse, maximum, reward):
    value = score(measurement(rmse, maximum), approved_rubric('s-204'), {'verdict': 'pass'})
    assert value['reward'] == pytest.approx(reward)
    assert value['verdict'] == ('pass' if reward == 1 else 'fail')
    assert not value['convergence_certified']


def test_bad_field_cannot_hide_behind_two_good_fields():
    value = measurement(); value['metrics']['T']['normalized_rmse'] = .3
    assert score(value, approved_rubric('s-204'), {'verdict':'pass'})['reward'] == 0


def test_pressure_gauge_policy_is_task_specific():
    value = measurement(); value['metrics']['p'].update(normalized_rmse=100, normalized_maximum_error=100)
    assert score(value, approved_rubric('s-203'), {'verdict':'pass'})['reward'] == 1
    assert score(value, approved_rubric('s-204'), {'verdict':'pass'})['reward'] == 0


@pytest.mark.parametrize('verdict,reward', [('review',None),('fail',0),('error',None)])
def test_no_automatic_reward_for_bad_or_uncertain_integrity(verdict, reward):
    result = score(measurement(), approved_rubric('s-203'), {'verdict':verdict})
    assert result['reward'] == reward and result['verdict'] != 'pass'
    assert result['metric_reward'] == 1 and len(result['field_scores']) == 3
    assert result['eligibility'] == {'fail':'invalid','review':'review','error':'error'}[verdict]


def test_missing_or_nonfinite_evidence_is_not_scored():
    value = measurement(); value['coverage'] = .99
    with pytest.raises(ValueError): score(value, approved_rubric('s-204'), {'verdict':'pass'})
    value = measurement(float('nan'), 0)
    with pytest.raises(ValueError): score(value, approved_rubric('s-204'), {'verdict':'pass'})


def native_fixture(tmp_path, *, initial_temperature=300, control_extra='', start=0):
    native = tmp_path / 'r-0000000000000001'
    work = native / 'inputs'
    (work / '0').mkdir(parents=True)
    (work / 'system').mkdir()
    (work / 'constant').mkdir()
    (work / 'system/controlDict').write_text(f'startFrom startTime; startTime {start};\n' + control_extra)
    dims = {'T':'[0 0 0 1 0 0 0]', 'U':'[0 1 -1 0 0 0 0]', 'p':'[0 2 -2 0 0 0 0]'}
    for field, value in [('T',str(initial_temperature)),('U','(0 0 0)'),('p','0')]:
        kind = 'volVectorField' if field == 'U' else 'volScalarField'
        (work / '0' / field).write_text(f'FoamFile {{format ascii; class {kind}; object {field}; location "0";}}\n'
                                      + f'dimensions {dims[field]}; internalField uniform {value}; boundaryField {{}}')
    write_once(native / 'spec.json', {'input_evidence':True,'kind':'run',
               'argv':['/opt/foam/bin/pimpleFoam'],'inputs':inventory(work)})
    write_once(native / 'dispatch.json', {'sequence': 1, 'state': 'dispatch_intent'})
    (native / 'stdout.log').write_text('Time = 0.1\nSolving for Ux\nTime = 1.5\nSolving for p\nEnd\n')
    runner = SimpleNamespace(root=tmp_path,
        sandbox=SimpleNamespace(foam_root=str(ROOT / 'environments/native-v2306/foam')),
        verify=lambda run_id: (tmp_path / run_id, {'success':True, 'kind':'run'}))
    reference = {'endpoint_kind':'physical_time','required_time':1.5,'dimensions':dims,
                 'initial_state':{'T':300,'U':[0,0,0],'p':0}}
    return runner, native, reference


def test_plain_provenance_passes(tmp_path):
    runner, native, reference = native_fixture(tmp_path)
    assert inspect(runner, native.name, reference)['verdict'] == 'pass'


def test_copied_target_temperature_as_initial_state_fails(tmp_path):
    runner, native, reference = native_fixture(tmp_path, initial_temperature=315)
    result = inspect(runner, native.name, reference)
    assert result['verdict'] == 'fail' and 'prescribed_initial_state_not_used:T' in result['reasons']


def test_code_hook_is_review_not_physics_failure(tmp_path):
    runner, native, reference = native_fixture(tmp_path, control_extra='functions { force { type coded; } }')
    assert inspect(runner, native.name, reference)['verdict'] == 'review'


def test_restart_without_a_prior_native_record_cannot_pass(tmp_path):
    runner, native, reference = native_fixture(tmp_path, start=1)
    (native / 'inputs/1').mkdir()
    assert inspect(runner, native.name, reference)['verdict'] == 'review'


def test_postprocessing_a_copied_field_is_not_evolution(tmp_path):
    runner, native, reference = native_fixture(tmp_path)
    (native / 'stdout.log').write_text('End\n')
    assert inspect(runner, native.name, reference)['verdict'] == 'fail'


def test_reward_recovery_never_regrades_or_changes_result(tmp_path):
    policy = {'rubric':approved_rubric('s-203')}
    value = {'reward':.5,'verdict':'fail','reason':'dense_reconstruction_below_full_credit'}
    publish_reward(tmp_path, value, policy)
    publish_reward(tmp_path, value, policy)
    assert read(tmp_path / 'reward.json')['reward'] == .5
    with pytest.raises(RuntimeError): publish_reward(tmp_path, {**value,'reward':1}, policy)


def test_verified_restart_from_a_short_run_is_allowed(tmp_path):
    import json
    import shutil
    runner, parent, reference = native_fixture(tmp_path)
    (parent / 'stdout.log').write_text('Time = 0.5\nSolving for Ux\nEnd\n')
    child = tmp_path / 'r-0000000000000002'
    shutil.copytree(parent / 'inputs', child / 'inputs')
    (child / 'inputs/0.5').mkdir()
    for field in ('U','T','p'):
        (child / 'inputs/0.5' / field).write_text('native restart fixture ' + field)
    (child / 'inputs/system/controlDict').write_text('startFrom latestTime; startTime 0;')
    hashes = inventory(child / 'inputs')
    write_once(child / 'spec.json', {**read(parent / 'spec.json'), 'inputs':hashes})
    write_once(child / 'dispatch.json', {'sequence': 2, 'state': 'dispatch_intent'})
    (child / 'stdout.log').write_text('Time = 1.5\nSolving for Ux\nEnd\n')
    write_once(parent / 'result.json', {'kind':'run','success':True,
              'artifacts':{k:v for k,v in hashes.items() if k.startswith('0.5/')}})
    result = inspect(runner, child.name, reference)
    assert result['verdict'] == 'pass' and result['parent'] == parent.name


def test_released_grade_writes_actual_reward_and_recovers_projection(tmp_path, monkeypatch):
    import json
    import shutil
    from agentcfd_bench.tasks.loader import Task
    from agentcfd_bench.grading import dense_native, dense_integrity
    source = ROOT / 'task-drafts/dense-observation-v1/s-203'
    target = tmp_path / 'task'; shutil.copytree(source, target)
    policy = read(target / 'private/grading.json')
    policy.update(release_status='released', rubric=approved_rubric('s-203'))
    (target / 'private/grading.json').write_text(json.dumps(policy))
    task = Task.load(target)
    native = tmp_path / 'native'; (native / 'artifacts').mkdir(parents=True)
    runner = SimpleNamespace(verify=lambda _: (native, {'kind':'run','success':True,'artifacts':{}}), sandbox=None)
    monkeypatch.setattr(dense_native, 'sample_case', lambda *a: measurement(.175,.2))
    monkeypatch.setattr(dense_integrity, 'inspect', lambda *a: {'verdict':'pass'})
    output = tmp_path / 'grading'
    result = dense_native.grade(task, runner, 'r-one', output)
    assert result['reward'] == pytest.approx(.5) and result['verdict'] == 'fail'
    (output / 'reward.json').unlink()  # Simulate interrupted projection publication.
    monkeypatch.setattr(dense_native, 'sample_case', lambda *a: pytest.fail('No second sampling'))
    assert dense_native.grade(task, runner, 'r-one', output) == result
    assert read(output / 'reward.json')['reward'] == pytest.approx(.5)


def test_report_keeps_review_out_of_reward_denominator(tmp_path):
    from agentcfd_bench.records.store import Store
    from agentcfd_bench.reports.summary import report
    for task_id, verdict, reward in [('a','pass',1),('b','not_evaluated',None)]:
        trial = tmp_path / 'trials' / task_id
        Store(trial).set('trial', {'lifecycle':'completed','verdict':verdict})
        write_once(trial / 'grading/result.json', {'verdict':verdict,'reward':reward,
                   'integrity_review_required':reward is None})
    value = report(tmp_path)
    assert value['registered'] == 2 and value['reward_denominator'] == 1
    assert value['review_required'] == 1 and value['mean_reward_scored'] == 1
    assert not value['rates_are_final']
