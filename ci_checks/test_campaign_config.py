import copy
import hashlib
import json
from pathlib import Path
import tomllib

import pytest
import yaml

import campaign_config as campaign
import submit_science as manual
from freeze_science_runtime import freeze

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config():
    value = campaign.read(PROJECT/'experiments/science.yaml', PROJECT)
    value['budget']['per_run_seconds'] = 300  # Most parameterized cases exercise old profiles.
    value['evidence'].pop('interface_check', None)  # Legacy profiles require their real probes.
    return value


def reread(tmp_path, value):
    file = tmp_path/'test.yaml'
    file.write_text(yaml.safe_dump(value, allow_unicode=True))
    return campaign.read(file, PROJECT)


def test_default_config_is_explicit_and_requires_fresh_launch_evidence(config, tmp_path):
    assert config['tasks'] == ['s-205','s-203','s-202','s-204']
    config['execution']['prepared_parent'] = str(tmp_path/'prepared')
    experiments, matrix = campaign.compile_inputs(config, PROJECT)
    assert all(e['task']['version'] == 'expert-output-v1' for e in experiments.values())
    assert all(row['positive_source'] is None for row in matrix['tasks'])
    path = tmp_path/'unprepared.yaml'
    path.write_text(yaml.safe_dump(config))
    result = manual.inspect(manual.load_plan(path))
    assert not result['ready'] and result['model_requests_sent'] == 0
    assert result['tasks'] == config['tasks']


@pytest.mark.parametrize('name,backend,model,effort,decision', [
    ('codex','chatgpt-subscription','gpt-5.6-sol','ultra',True),
    ('codex','chatgpt-subscription','gpt-6-astra','xhigh',True),
    ('codex','custom-api','AWS-Claude-Fable-5',None,False),
    ('codex','custom-api','Kimi-K3',None,False),
    ('foamclaw','custom-api','Kimi-K3',None,False),
    ('claude-code','custom-api','Kimi-K3',None,False),
    ('kimi-code','custom-api','Kimi-K3',None,False),
])
def test_supported_settings_compile_into_actual_runner_inputs(config, tmp_path, name, backend, model, effort, decision):
    config['instruction_profile'] = 'registered-v1'
    config['harness'] = dict(name=name, backend=backend, reasoning_effort=effort, public_decision_log=decision)
    config['model']['name'] = model
    config['authentication'] = {'auth_home':'/does/not/exist'} if backend == 'chatgpt-subscription' else {'env_file':'/does/not/exist.env'}
    config['tasks'] = ['s-205','s-001']
    config['budget']['model_calls'] = 17
    value = reread(tmp_path, config)
    experiments, manifest = campaign.compile_inputs(value, PROJECT)
    assert manifest['harness'] == name
    assert [row['experiment'] for row in manifest['tasks']] == ['yaml-generated-s-205.json','yaml-generated-s-001.json']
    assert manifest['tasks'][1]['positive_source'] is None
    for item in experiments.values():
        assert item['model']['name'] == model and item['budget']['model_calls'] == 17
        assert 'max_output_tokens' not in item['budget']
        assert item.get('harness', {}).get('backend','custom-api') == backend
        from agentcfd_bench.spec import prepare
        assert prepare(item)['static_ready']


@pytest.mark.parametrize('field,value', [
    ('tasks',[]), ('tasks',['s-999']), ('tasks',['s-105','s-105']),
    ('model',{'name':'Opus-5'}), ('model',{'name':'Kimi-K2.6'}), ('model',{'name':'Qwen3.7'}),
    ('documentation','internet'), ('instruction_profile','random'),
    ('name','../escape'), ('unknown',1),
])
def test_invalid_choices_never_silently_fall_back(config, tmp_path, field, value):
    config[field] = value
    with pytest.raises(ValueError):
        reread(tmp_path, config)


@pytest.mark.parametrize('body', [
    'version: a\nversion: b\n', 'x: &a [1]\ny: *a\n',
    'x: !!python/object/apply:os.system ["false"]\n', 'x: {<<: {a: 1}}\n',
])
def test_yaml_rejects_ambiguous_or_executable_constructs(tmp_path, body):
    path = tmp_path/'bad.yaml'
    path.write_text(body)
    with pytest.raises(ValueError):
        campaign.read(path, PROJECT)


@pytest.mark.parametrize('change', ['subscription_other_harness','other_model_non_codex','custom_effort','tokens','concurrency','native_budget','bool_rounds'])
def test_unsupported_capabilities_fail_before_any_prepare(config, tmp_path, change):
    if change == 'subscription_other_harness':
        config['harness']['name'] = 'foamclaw'
    elif change in ('other_model_non_codex','custom_effort'):
        config['harness'].update(name='foamclaw',backend='custom-api',reasoning_effort=None,public_decision_log=False)
        config['authentication'] = {'env_file':'never-opened.env'}
        if change == 'custom_effort':
            config['model']['name'] = 'Kimi-K3'
            config['harness']['reasoning_effort'] = 'high'
    elif change == 'tokens':
        config['budget']['max_output_tokens'] = 100
    elif change == 'concurrency':
        config['execution']['provider_concurrency'] = 4
    elif change == 'native_budget':
        config['budget']['per_run_seconds'] = 1801
    else:
        config['budget']['model_calls'] = True
    with pytest.raises(ValueError):
        reread(tmp_path, config)


def test_prepare_snapshots_once_no_secrets_and_hashes_generated_configs(config, tmp_path):
    config['instruction_profile'] = 'registered-v1'
    config['execution']['prepared_parent'] = str(tmp_path)
    result = campaign.prepare(config, PROJECT)
    root = Path(result['prepared'])
    runtime = root/'runtime'
    assert result['model_requests_sent'] == 0 and not result['paid_ready']
    assert not (runtime/'runs').exists() and not (runtime/'auth.json').exists()
    snapshot = json.loads((runtime/'snapshot.json').read_text())
    assert snapshot['files']['experiments/yaml-matrix.json'] == hashlib.sha256((runtime/'experiments/yaml-matrix.json').read_bytes()).hexdigest()
    assert json.loads((runtime/'experiments/yaml-generated-s-205.json').read_text())['budget'] == config['budget']
    with pytest.raises(FileExistsError):
        campaign.prepare(config, PROJECT)
    from agentcfd_bench.task_package import task_digest
    registry = tomllib.loads((runtime/'tasks/dataset.toml').read_text())
    for row in registry['tasks']:
        assert task_digest(runtime/'tasks'/row['id']) == row['digest']
    # Configuration edits require another immutable preparation, not mutation.
    file = tmp_path/'campaign.yaml'
    file.write_text(yaml.safe_dump(config))
    plan = manual.load_plan(file)
    config['tasks'] = ['s-205']
    file.write_text(yaml.safe_dump(config))
    changed = manual.inspect(manual.load_plan(file))
    assert any('YAML changed after prepare' in x for x in changed['blockers'])
    assert not any('Prepare evidence:' in x for x in manual.inspect(plan)['blockers'])
    (runtime/'experiments/yaml-generated-s-205.json').write_text('{}')
    assert any('Prepared experiment differs' in x for x in manual.inspect(plan)['blockers'])


def test_all_registered_tasks_have_short_review_only_briefs():
    registry = tomllib.loads((PROJECT/'tasks/dataset.toml').read_text())
    for row in registry['tasks']:
        text = (PROJECT/'task-drafts/physics-intent-v1'/row['id']/'instruction.md').read_text()
        assert len(text.splitlines()) < 45
        assert 'OpenFOAM' in text and '文档' in text
        assert all(word not in text for word in ('boundaryField','thermoType','reference_dictionary','```','FoamFile','/root/'))


def test_legacy_json_still_loads_without_compilation():
    plan = manual.load_plan('experiments/sol-ultra-five-manual-v1.json')
    assert plan['campaign'] is None
    assert manual.inspect(plan)['tasks'] == ['s-105','s-205','s-203','s-202','s-204']


def test_free_mesh_selects_exact_version_and_never_imports_old_baseline(config):
    config['tasks'] = ['s-001']
    config['instruction_profile'] = 'geometry-only-free-mesh-v1'
    experiments, matrix = campaign.compile_inputs(config, PROJECT)
    experiment = experiments['experiments/yaml-generated-s-001.json']
    assert experiment['task']['version'] == 'free-mesh-v1'
    assert matrix['tasks'][0]['positive_source'] is None
    from agentcfd_bench.spec import prepare
    assert prepare(experiment)['static_ready']


def test_free_mesh_review_case_blocks_whole_selection_without_fallback(config, tmp_path):
    config['tasks'] = ['s-001', 's-202']
    config['instruction_profile'] = 'geometry-only-free-mesh-v1'
    config['execution']['prepared_parent'] = str(tmp_path/'prepared')
    with pytest.raises(ValueError, match='retained for review'):
        campaign.prepare(config, PROJECT)
    assert not (tmp_path/'prepared').exists()
    assert config['tasks'] == ['s-001', 's-202']


@pytest.mark.parametrize('name', campaign.HARNESSES)
@pytest.mark.parametrize('profile', ['registered-v1', 'geometry-only-free-mesh-v1'])
def test_real_matrix_and_single_task_cli_forward_harness_without_dispatch(config, tmp_path, monkeypatch, name, profile):
    """Exercise both existing CLI entrypoints; replace only external work."""
    from types import SimpleNamespace
    import run_science_matrix as matrix
    import run_codex_science as single
    from agentcfd_bench import qualification, runtime, engine
    from agentcfd_bench.smoke import agent
    from agentcfd_bench.journal import NativeJournal
    config['tasks'] = ['s-001']
    config['instruction_profile'] = profile
    config['model']['name'] = 'Kimi-K3'
    config['harness'] = dict(name=name,backend='custom-api',reasoning_effort=None,public_decision_log=False)
    experiments, manifest = campaign.compile_inputs(config, PROJECT)
    # Existing matrix resolves experiments under its project, no new agent loop.
    (tmp_path/'experiments').mkdir()
    for relative, value in experiments.items():
        (tmp_path/relative).write_text(json.dumps(value))
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    probe = NativeJournal(tmp_path/'probe')
    probe.write('result', {'passed':True,'benchmark_score':False})
    probe.write('spec', {'model':{'name':'Kimi-K3','wire_api':'chat'}, 'harness_identity':{'name':name}})
    monkeypatch.setattr(matrix, 'qualify', lambda *a, **kw: {'passed':True,'checks':{'fixture':True}})
    monkeypatch.setattr(matrix, 'cluster_service', lambda *a, task: SimpleNamespace(task_identity=task.binding))
    commands = []
    class Child:
        pid = 999999999
        def __init__(self, command, **kwargs):
            commands.append(command)
        def wait(self):
            return 0
    monkeypatch.setattr(matrix.subprocess, 'Popen', Child)
    assert matrix.main(['--project',str(tmp_path),'--source-project',str(PROJECT),
        '--manifest',str(tmp_path/'manifest.json'),'--root',str(tmp_path/'matrix'),
        '--probe',str(tmp_path/'probe'),'--env-file','/fake-only','--allow-paid']) == 0
    assert len(commands) == 1 and commands[0][commands[0].index('--harness')+1] == name
    # Now exercise the child entrypoint and inspect the actual factory argument.
    observed = []
    monkeypatch.setattr(qualification, 'require_qualified', lambda *a, **k: None)
    monkeypatch.setattr(runtime, 'cluster_service', lambda *a, task: SimpleNamespace(task_identity=task.binding))
    def fake_factory(root, selected, **kwargs):
        observed.append((selected, kwargs))
        return SimpleNamespace(identity={'name':selected})
    monkeypatch.setattr(agent, 'factory', fake_factory)
    monkeypatch.setattr(engine, 'run', lambda *a, **kw: {'lifecycle':'completed'})
    env = tmp_path/'fake.env'
    env.write_text('SCIENCE_API_BASE=https://invalid.example\nSCIENCE_API_KEY=FAKE_NO_REQUEST\n')
    assert single.main(['--experiment',str(tmp_path/'experiments/yaml-generated-s-001.json'),
        '--harness',name,'--root',str(tmp_path/'single'),'--qualification',str(tmp_path/'unused'),
        '--legacy-root',str(PROJECT.parent),'--env-file',str(env),'--allow-paid']) == 0
    assert observed[0][0] == name and observed[0][1]['model'] == 'Kimi-K3'


def test_durable_exit_wins_over_stale_running_state(tmp_path, monkeypatch):
    import run_science_matrix as matrix
    from agentcfd_bench.journal import NativeJournal
    (tmp_path/'trials/a').mkdir(parents=True)
    (tmp_path/'trials/a/state.sqlite').touch()
    NativeJournal(tmp_path/'campaign').write('a', {'status':'trial_exited','returncode':1})
    monkeypatch.setattr(matrix, 'report', lambda *a, **k: dict(lifecycle='running',verdict='error',
        reason='fixture',model_calls=0,run_submissions=0,native_runs_completed=0,report_failures=0,usage={}))
    result = matrix.summary(tmp_path, [{'task':'a'}])
    assert result['finished'] == 1 and result['tasks'][0]['status'] == 'trial_exited'
    assert 'GPT-5.6' not in (tmp_path/'scoreboard.md').read_text()


def test_snapshot_does_not_copy_nested_credentials_or_follow_symlinks(tmp_path):
    project = tmp_path/'project'
    for name in ('agentcfd_bench','tasks','resources','experiments','ci_checks'):
        (project/name).mkdir(parents=True)
    for name in ('private.env', '.env.production', 'auth.json', 'unusual-secret.txt'):
        (project/'experiments'/name).write_text('FAKE_SECRET')
    freeze(project, tmp_path/'snapshot', excluded=[project/'experiments/unusual-secret.txt'])
    assert not list((tmp_path/'snapshot/experiments').iterdir())
    with pytest.raises(ValueError, match='copied source'):
        freeze(project, project/'experiments/recursive-copy')
    assert not (project/'experiments/recursive-copy').exists()
    (project/'resources/link').symlink_to(project/'experiments/unusual-secret.txt')
    with pytest.raises(ValueError, match='symlink'):
        freeze(project, tmp_path/'unsafe')


def test_clearing_release_flag_does_not_publish_a_draft(config, tmp_path, monkeypatch):
    config['release'] = dict(ready=True,audit_report='fixture.md',blockers=[])
    file = tmp_path/'draft.yaml'
    file.write_text(yaml.safe_dump(config))
    monkeypatch.setattr(manual.subprocess, 'run', lambda *a, **k: pytest.fail('draft dispatched'))
    assert manual.main(['submit','--config',str(file),'--run-name','must-not-run','--allow-paid']) == 2
