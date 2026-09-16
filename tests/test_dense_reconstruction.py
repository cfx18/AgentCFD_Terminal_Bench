"""Public-observation exports and pure metrics: no paid service or solver."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from agentcfd_bench.grading.dense import observations, compare, align_samples
from agentcfd_bench.grading.dense_native import select_time, InvalidNativeFields, sampling_dictionary
from agentcfd_bench.harnesses.codex import PROTOCOL, protocol_for
from agentcfd_bench.tasks.loader import Task
from agentcfd_bench.tasks.reconstruction import export

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / 'task-drafts/dense-observation-v1'


@pytest.fixture(scope='module', params=['s-203', 's-204'])
def dense(request):
    task = Task.load(DRAFT / request.param)
    schema, data = observations(task.root / 'public')
    return task, schema, data


def prediction(data):
    return {'U': data[:, 4:7].copy(), 'p': data[:, 7].copy(), 'T': data[:, 8].copy()}


def test_export_is_bound_to_selected_reference(dense):
    task, schema, data = dense
    private, _ = task.private()
    assert private['public_csv_sha256'] == schema['csv_sha256']
    old = json.loads((ROOT / 'tasks/releases/expert-output-v1' / task.task_id / 'solution/accepted-target.json').read_text())
    assert private['source'] == old['source']
    assert len(data) == (68107 if task.task_id == 's-203' else 78750)
    assert data[:, 3].sum() == pytest.approx(.000248 if task.task_id == 's-203' else .076 * 2.18 * .52)


def test_self_comparison_zero_but_not_approved_pass(dense):
    _, schema, data = dense
    result = compare(data, prediction(data), schema)
    assert all(row['rmse'] == row['maximum_absolute_error'] == 0 for row in result['metrics'].values())
    assert result['verdict'] == 'not_evaluated' and result['reward'] is None
    assert not result['convergence_certified'] and result['integrity_review_required']


def test_small_temperature_error_not_diluted_by_absolute_kelvin(dense):
    task, schema, data = dense
    pred = prediction(data); pred['T'] += .01
    result = compare(data, pred, schema)['metrics']['T']
    assert result['rmse'] == pytest.approx(.01)
    if task.task_id == 's-203':
        assert .10 < result['normalized_rmse'] < .12


def test_vector_direction_and_pressure_offset_are_not_discarded(dense):
    _, schema, data = dense
    pred = prediction(data); pred['U'] *= -1; pred['p'] += 5
    result = compare(data, pred, schema)['metrics']
    assert result['U']['normalized_rmse'] == pytest.approx(2)
    assert result['p']['rmse'] == pytest.approx(5)
    assert result['p']['gauge_aligned_rmse'] < 1e-10


def test_local_error_is_visible_even_with_small_average(dense):
    _, schema, data = dense
    pred = prediction(data); pred['T'][0] += 10
    result = compare(data, pred, schema)['metrics']['T']
    assert result['maximum_absolute_error'] == pytest.approx(10)
    assert result['rmse'] < 1


@pytest.mark.parametrize('bad', ['nan', 'negative_temperature', 'missing_field', 'missing_row', 'numeric_overflow'])
def test_invalid_samples_never_become_success(dense, bad):
    _, schema, data = dense
    pred = prediction(data)
    if bad == 'nan': pred['T'][0] = np.nan
    elif bad == 'negative_temperature': pred['T'][0] = -1
    elif bad == 'missing_field': pred.pop('p')
    elif bad == 'numeric_overflow': pred['U'][0] = 1e308
    else: pred['U'] = pred['U'][:-1]
    with pytest.raises(ValueError): compare(data, pred, schema)


def test_reordering_is_not_a_field_error(dense):
    _, _, data = dense
    assert np.array_equal(align_samples(data[::-1, :3], data[::-1, 8], data[:, :3]), data[:, 8])


@pytest.mark.parametrize('bad', ['missing', 'duplicate', 'shifted'])
def test_points_cannot_be_silently_dropped_or_extrapolated(dense, bad):
    _, _, data = dense
    c, t = data[:, :3].copy(), data[:, 8].copy()
    if bad == 'missing': c, t = c[:-1], t[:-1]
    elif bad == 'duplicate': c[0] = c[1]
    else: c[:, 0] += .001
    with pytest.raises(ValueError): align_samples(c, t, data[:, :3])


def test_public_bundle_does_not_leak_original_configuration(dense):
    task, _, _ = dense
    for path in (task.root / 'public').rglob('*'):
        if path.is_file():
            text = path.read_text()
            assert not any(term in text for term in ('AgentCFD', '/root/', 'accepted-target', 'boundaryField',
                                                     'ArrheniusBirdCarreau', 'kOmegaSST', 'kEpsilon'))
    stl = (task.root / 'public/geometry/domain.stl').read_text()
    assert 'solid hot' not in stl and 'solid cold' not in stl and 'solid inlet' not in stl
    original = (ROOT / 'tasks/releases/workbench-v3' / task.task_id / 'public/geometry/domain.stl').read_text()
    assert [line for line in stl.splitlines() if line.strip().startswith('vertex')] == [
        line for line in original.splitlines() if line.strip().startswith('vertex')]


def test_prompt_does_not_deny_access_to_public_target(dense):
    task, _, _ = dense
    prompt = protocol_for(task)
    assert 'intentionally public' in prompt
    assert 'GT comparison is private' not in prompt
    assert 'reference\nanswers and graders are not accessible' not in prompt
    assert 'Original source cases' in prompt
    assert protocol_for(Task.load(ROOT / 'tasks/releases/workbench-v3' / task.task_id)) == PROTOCOL


def test_public_protocol_declares_serial_only_execution(dense):
    task, _, _ = dense
    for prompt in (PROTOCOL, protocol_for(task)):
        assert 'OpenFOAM solver execution in this environment is serial-only.' in prompt
        assert 'do not use mpirun, mpiexec, or the solver\'s -parallel option' in prompt
        assert 'plan for serial execution' in prompt


def test_export_refuses_overwriting_existing_draft():
    with pytest.raises(FileExistsError): export(DRAFT, ROOT)


def test_csv_tampering_is_detected(tmp_path):
    public = DRAFT / 's-203/public'
    shutil.copytree(public / 'observations', tmp_path / 'observations')
    path = tmp_path / 'observations/fields.csv'
    with path.open('a') as out: out.write('\n')
    with pytest.raises(ValueError, match='changed'): observations(tmp_path)


def test_steady_reference_is_not_6000_seconds():
    schema, _ = observations(DRAFT / 's-204/public')
    assert schema['snapshot']['physical_time'] is None
    ref, _ = Task.load(DRAFT / 's-204').private()
    assert ref['endpoint_kind'] == 'latest_saved_state' and ref['required_time'] is None


def test_sampler_receives_coordinates_not_target_values(dense):
    _, _, data = dense
    text = sampling_dictionary(data[:2, :3], 'dense_0123456789abcdef')
    assert 'interpolationScheme cell;' in text
    assert 'fields (T)' in text and 'type sets' in text
    assert 'native_executable' not in text and '315.090816863' not in text
    assert 'functions' in text and 'systemCall' not in text


def test_missing_endpoint_is_invalid_not_fabricated(tmp_path):
    reference, _ = Task.load(DRAFT / 's-203').private()
    (tmp_path / '1.0').mkdir()
    with pytest.raises(InvalidNativeFields): select_time(tmp_path, reference)


def test_draft_prepare_cannot_be_unlocked_by_mesh_flag_alone(monkeypatch):
    from agentcfd_bench.tasks import experiment
    from agentcfd_bench.execution.sandbox import Sandbox
    monkeypatch.setattr(Sandbox, 'probe', lambda self: {'filesystem': 'mock', 'network': 'mock'})
    monkeypatch.setattr(experiment, 'verify_runtime', lambda *args: None)
    original = Task.private
    def pretend_mesh_qualified(self):
        reference, policy = original(self)
        policy['general_mesh_qualified'] = True
        return reference, policy
    monkeypatch.setattr(Task, 'private', pretend_mesh_qualified)
    result = experiment.prepare(ROOT / 'experiments/dense-reconstruction-draft.yaml')
    assert not result['ready'] and result['paid_calls'] == 0
    assert sum('rubric and integrity' in text for text in result['blockers']) == 2
    assert not any('unrestricted-mesh grader' in text for text in result['blockers'])
