"""Real-client probe routing tests; no credentials, model requests or native jobs."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import probe_codex_client as probe
from agentcfd_bench.journal import read_receipt
from agentcfd_bench.spec import load_experiment


@pytest.mark.parametrize('harness', ['codex', 'kimi-code'])
@pytest.mark.parametrize('model', ['Kimi-K3', 'kimi-k3'])
@pytest.mark.parametrize('docs_used', [True, False])
def test_probe_routes_selected_client_and_requires_real_doc_observation(tmp_path, monkeypatch, harness, model, docs_used):
    import dotenv
    project = Path(__file__).resolve().parents[1]
    experiment = load_experiment(project/'experiments/science-docs-calibration-v1.json')
    experiment['model']['name'] = model
    monkeypatch.setattr('agentcfd_bench.spec.load_experiment', lambda _: copy.deepcopy(experiment))
    monkeypatch.setattr(dotenv, 'dotenv_values', lambda _: {
        'OPENAI_BASE_URL': 'https://invalid.example/v1', 'OPENAI_API_KEY': 'FAKE_SECRET'})
    observed = []
    closed = []
    class Fake:
        identity = {'name': harness, 'model': model}
        def step(self, context):
            assert context.remaining_calls == 6
            return SimpleNamespace(files={'system/interface-check.json': '{"ok":true}'},
                model_calls=3, usage={'documentation': {'queries': int(docs_used)}},
                submitted=True, input_error=None)
        def close(self):
            closed.append(True)
    def factory(root, selected, **kwargs):
        assert kwargs['model'] == model
        assert kwargs['credential'] == 'FAKE_SECRET'
        observed.append(selected)
        return lambda _: Fake()
    monkeypatch.setattr(probe, 'factory', factory)
    root = tmp_path/'probe'
    result = probe.main(['--harness', harness, '--env-file', 'never-read.env',
        '--experiment', 'mock.json', '--root', str(root), '--max-calls', '6', '--allow-paid'])
    assert result == (0 if docs_used else 1)
    assert observed == [harness] and closed == [True]
    assert read_receipt(root/'spec.json')['harness_identity']['name'] == harness
    assert read_receipt(root/'result.json')['benchmark_score'] is False
    assert 'FAKE_SECRET' not in ''.join(p.read_text() for p in root.rglob('*.json'))
    with pytest.raises(FileExistsError):
        probe.main(['--harness', harness, '--env-file', 'never-read.env',
            '--experiment', 'mock.json', '--root', str(root), '--allow-paid'])


@pytest.mark.parametrize('extra,model', [({'backend':'chatgpt-subscription'}, 'gpt-6-astra'), ({}, 'gpt-5.6-sol')])
def test_kimi_probe_cannot_silently_use_another_backend_or_model(tmp_path, monkeypatch, extra, model):
    monkeypatch.setattr('agentcfd_bench.spec.load_experiment', lambda _: {
        'harness': extra, 'model': {'name':model}})
    monkeypatch.setattr(probe, 'factory', lambda *a, **kw: pytest.fail('Must reject before client creation'))
    root = tmp_path/'probe'
    with pytest.raises(SystemExit) as exc:
        probe.main(['--harness','kimi-code','--env-file','never-read.env',
            '--experiment','mock.json','--root',str(root),'--allow-paid'])
    assert exc.value.code == 2 and not root.exists()


def test_kimi_campaign_keeps_astra_task_conditions_but_separates_identity_and_run():
    import campaign_config
    project = Path(__file__).resolve().parents[1]
    astra = campaign_config.read(project/'experiments/science.yaml', project)
    kimi = campaign_config.read(project/'experiments/science-kimi-code.yaml', project)
    for key in ('tasks', 'instruction_profile', 'budget', 'documentation'):
        assert kimi[key] == astra[key]
    assert kimi['harness']['name'] == 'kimi-code' and kimi['model']['name'] == 'Kimi-K3'
    assert kimi['name'] != astra['name']
    experiments, manifest = campaign_config.compile_inputs(kimi, project)
    assert manifest['harness'] == 'kimi-code'
    for value in experiments.values():
        assert value['model'] == {'name':'Kimi-K3', 'wire_api':'chat'}
        assert value['task']['version'] == 'expert-output-v1'


def test_official_kimi_config_never_reuses_relay_credentials_or_qualification(tmp_path):
    import campaign_config
    import submit_science
    project = Path(__file__).resolve().parents[1]
    old = campaign_config.read(project/'experiments/science-kimi-code.yaml', project)
    new_path = project/'experiments/science-kimi-official.yaml'
    new = campaign_config.read(new_path, project)
    assert not old['release']['ready'] and old['release']['blockers']
    assert new['model']['name'] == 'kimi-k3'
    assert new['name'] != old['name']
    assert new['authentication'] == {'env_file': '.env.kimi-official'}
    assert new['evidence']['probe'] != old['evidence']['probe']
    assert new['evidence']['junit'] != old['evidence']['junit']
    for key in ('tasks', 'instruction_profile', 'budget', 'documentation'):
        assert new[key] == old[key]
    experiments, _ = campaign_config.compile_inputs(new, project)
    assert all(x['model']['name'] == 'kimi-k3' for x in experiments.values())
    # A pending review is always blocking; don't tie tests to today's live readiness.
    pending = copy.deepcopy(new)
    pending['release'] = {**pending['release'], 'ready': False, 'blockers': ['test review pending']}
    import yaml
    pending_path = tmp_path/'pending.yaml'
    pending_path.write_text(yaml.safe_dump(pending))
    checked = submit_science.inspect(submit_science.load_plan(pending_path))
    assert not checked['ready'] and checked['model_requests_sent'] == 0
    assert 'test review pending' in checked['blockers']
