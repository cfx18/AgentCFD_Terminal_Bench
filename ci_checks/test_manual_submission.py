"""No live authentication, socket, subprocess, model request, or native job."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from agentcfd_bench.journal import NativeJournal
import submit_science as manual


def fake_test_evidence(runtime, path):
    """Only a unit-test fixture; no production receipt signing/export route."""
    from release_evidence import REQUIRED, REQUIRED_GROUPS, sources, summary, sidecar, VERSION
    (runtime/'tests').mkdir(exist_ok=True)
    for module in REQUIRED_GROUPS:
        file = runtime/'tests'/f'{module}.py'
        if not file.exists():
            file.write_text('# fixture representing a reviewed test module\n')
    cases = ''.join(f'<testcase classname="tests.{module}" name="{name}"/>' for module,name in sorted(REQUIRED))
    path.write_text(f'<testsuite tests="{len(REQUIRED)}" failures="0" errors="0" skipped="0">{cases}</testsuite>')
    result = summary(path)
    bound = sources(runtime)
    sidecar(path).write_text(json.dumps({'version': VERSION, 'sources_before': bound, 'sources_after': bound,
        'junit_sha256': result['sha256'], 'cases': result['cases'], 'exit_code': 0}))


@pytest.fixture
def plan(tmp_path):
    project = tmp_path/'project'
    project.mkdir()
    (project/'ci_checks').mkdir()
    (project/'ci_checks/launch_science_matrix.py').write_text('# mocked launcher: no execution\n')
    runtime = project/'runtime'
    (runtime/'experiments').mkdir(parents=True)
    (runtime/'agentcfd_bench/adapters').mkdir(parents=True)
    source = runtime/'agentcfd_bench/adapters/fixture.py'
    source.write_text('# no execution\n')
    experiment = {'task': {'id': 's-test'}, 'model': {'name': 'gpt-5.6-sol', 'wire_api': 'responses'},
                  'budget': {'model_calls': 64},
                  'harness': {'backend': 'chatgpt-subscription', 'reasoning_effort': 'ultra'}}
    (runtime/'experiments/a.json').write_text(json.dumps(experiment))
    (project/'manifest.json').write_text(json.dumps({'version': 'explicit-science-matrix-v1',
        'provider_concurrency': 1, 'native_concurrency': 1, 'tasks': [{'experiment': 'a.json'}]}))
    probe = NativeJournal(project/'probe')
    probe.write('result', {'passed': True, 'benchmark_score': False})
    probe.write('spec', {'model': experiment['model'], 'harness_identity': {
        'backend': 'chatgpt-subscription', 'reasoning_effort': 'ultra',
        'bridge_source_hashes': {'adapters/fixture.py': hashlib.sha256(source.read_bytes()).hexdigest()}}})
    fake_test_evidence(runtime, project/'tests.xml')
    binary = project/'venv/bin/python'
    binary.parent.mkdir(parents=True)
    binary.symlink_to('/usr/bin/python3')
    config = {'version': 'manual-science-launch-v1', 'python': 'venv/bin/python',
        'runtime': 'runtime', 'manifest': 'manifest.json', 'probe': 'probe', 'junit': ['tests.xml'],
        'model': 'gpt-5.6-sol', 'reasoning_effort': 'ultra', 'model_calls_per_task': 64,
        'authentication': {'backend': 'chatgpt-subscription', 'auth_home': '/private/host-login'},
        'output_parent': 'runs/manual', 'release': {'ready': True, 'audit_report': 'audit.md', 'blockers': []}}
    (project/'manual.json').write_text(json.dumps(config))
    return manual.load_plan('manual.json', project)


def test_readiness_checks_real_receipt_hash_and_preserves_venv(plan):
    assert manual.inspect(plan)['ready']
    assert str(plan['python']).endswith('/venv/bin/python')
    assert plan['python'] != plan['python'].resolve()
    assert not plan['output_parent'].exists()


def test_tampered_probe_and_changed_bridge_are_blocked(plan):
    (plan['runtime']/'agentcfd_bench/adapters/fixture.py').write_text('changed')
    assert not manual.inspect(plan)['ready']
    path = plan['probe']/'result.json'
    record = json.loads(path.read_text())
    record['payload']['benchmark_score'] = True
    path.write_text(json.dumps(record))
    assert any('checksum' in s for s in manual.inspect(plan)['blockers'])


@pytest.mark.parametrize('key,value', [('model', 'other'), ('reasoning_effort', 'high'), ('model_calls_per_task', 32)])
def test_task_configuration_drift_is_blocked(plan, key, value):
    plan['value'][key] = value
    assert not manual.inspect(plan)['ready']


@pytest.mark.parametrize('name', ['../escape', '/tmp/run', '.', '', 'a/b', '-flag'])
def test_run_name_cannot_escape_output_parent(plan, name):
    with pytest.raises(ValueError):
        manual.run_paths(plan, name)


def test_submit_needs_paid_flag_and_reviewed_release(plan, monkeypatch):
    monkeypatch.setattr(manual, 'load_plan', lambda _: plan)
    monkeypatch.setattr(manual.subprocess, 'run', lambda *a, **k: pytest.fail('unexpected process launch'))
    assert manual.main(['submit', '--run-name', 'a']) == 2
    plan['value']['release']['ready'] = False
    assert manual.main(['submit', '--run-name', 'a', '--allow-paid']) == 2
    assert not plan['output_parent'].exists()


def test_submit_reuses_detached_launcher_without_waiting_for_model(plan, monkeypatch):
    monkeypatch.setattr(manual, 'load_plan', lambda _: plan)
    calls = []
    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(manual.subprocess, 'run', launch)
    assert manual.main(['submit', '--run-name', 'a', '--allow-paid']) == 0
    command, options = calls[0]
    assert len(calls) == 1 and command[0] == str(plan['python'])
    assert '--auth-home' in command and '--env-file' not in command
    assert command[3].endswith('/snapshots/controller/launch_science_matrix.py')
    from pathlib import Path
    assert Path(command[3]).read_bytes() == (plan['project']/'ci_checks/launch_science_matrix.py').read_bytes()
    assert 'model_requests_sent' not in options


def test_existing_run_cannot_be_resubmitted(plan, monkeypatch):
    monkeypatch.setattr(manual, 'load_plan', lambda _: plan)
    manual.run_paths(plan, 'a')[0].mkdir(parents=True)
    monkeypatch.setattr(manual.subprocess, 'run', lambda *a, **k: pytest.fail('duplicate dispatch'))
    assert manual.main(['submit', '--run-name', 'a', '--allow-paid']) == 2


def test_status_never_creates_state_or_starts_process(plan, monkeypatch):
    monkeypatch.setattr(manual, 'load_plan', lambda _: plan)
    monkeypatch.setattr(manual.subprocess, 'run', lambda *a, **k: pytest.fail('read-only status launched process'))
    assert manual.main(['status', '--run-name', 'a']) == 0
    assert not plan['output_parent'].exists()


def test_custom_api_command_does_not_read_key_or_use_subscription(plan):
    custom = copy.deepcopy(plan)
    custom['value']['authentication'] = {'backend': 'custom-api', 'env_file': '/private/not-opened.env'}
    custom['value']['reasoning_effort'] = None
    command = manual.launch_command(custom, 'fable-a')
    assert '--env-file' in command and '--auth-home' not in command
    assert '/private/not-opened.env' in command


def test_shipped_configuration_is_deliberately_blocked():
    value = manual.inspect(manual.load_plan('experiments/sol-ultra-five-manual-v1.json'))
    assert value['ready'] is False and value['blockers']
    assert value['tasks'] == ['s-105', 's-205', 's-203', 's-202', 's-204']
    assert value['model_requests_sent'] == 0


def test_partial_junit_blocks_without_launch(plan):
    plan['junit'][0].write_text('<testsuite')
    assert manual.inspect(plan)['ready'] is False
