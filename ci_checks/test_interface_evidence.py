import copy
import pytest

from interface_evidence import KIND, validate


def fixture():
    spec = {'kind':KIND,'model':{'name':'gpt-6-astra','wire_api':'responses'},
        'harness_identity':{'name':'codex','backend':'chatgpt-subscription','reasoning_effort':'xhigh'},
        'test_junit_sha256':['local-test-sha']}
    result = {'passed':True,'benchmark_score':False,'provider_verified':False,'model_requests_sent':0}
    tests = {'passed':True,'shards':[{'sha256':'local-test-sha','cases':[
        {'name':'test_real_astra_xhigh_client_tools_docs_isolation_and_resume','status':'pass'}]}]}
    return spec, result, tests


def test_local_gate_never_claims_online_probe():
    spec, result, tests = fixture()
    validate('local-only',spec,result,tests=tests)
    with pytest.raises(ValueError,match='mode'):
        validate('live-probe',spec,result,tests=tests)
    with pytest.raises(ValueError,match='mode'):
        validate('local-only',{},result)


@pytest.mark.parametrize('change',['model','effort','paid','provider','hash','skipped','other_test','failed'])
def test_local_gate_requires_exact_successful_client_evidence(change):
    spec, result, tests = fixture()
    if change == 'model': spec['model']['name']='Kimi-K3'
    elif change == 'effort': spec['harness_identity']['reasoning_effort']='ultra'
    elif change == 'paid': result['model_requests_sent']=1
    elif change == 'provider': result['provider_verified']=True
    elif change == 'hash': spec['test_junit_sha256']=['other']
    elif change == 'skipped': tests['shards'][0]['cases'][0]['status']='skipped'
    elif change == 'other_test': tests['shards'][0]['cases'][0]['name']='test_real_xhigh_client_tools_docs_isolation_and_resume'
    else: tests['passed']=False
    with pytest.raises(ValueError): validate('local-only',spec,result,tests=tests)


def test_legacy_real_api_gate_remains_available():
    validate('live-probe', {'model':{'name':'Kimi-K3'}}, {'passed':True,'benchmark_score':False})


def test_astra_custom_chat_is_not_silently_accepted(tmp_path):
    from pathlib import Path
    import yaml
    import campaign_config
    project = Path(__file__).resolve().parents[1]
    value = campaign_config.read(project/'experiments/science.yaml',project)
    value['harness'].update(backend='custom-api',reasoning_effort=None,public_decision_log=False)
    value['authentication']={'env_file':'never-read.env'}
    value['evidence'].pop('interface_check',None)
    with pytest.raises(ValueError,match='Responses'):
        campaign_config.read(tmp_path/'unused',project,text=yaml.safe_dump(value))


def test_new_task_lease_covers_approved_native_budget(tmp_path, monkeypatch):
    from agentcfd_bench.runtime import cluster_service
    from agentcfd_bench.task_package import load_task
    from agentcfd_bench.adapters import cluster_native
    leases = []
    original = cluster_native.SlurmLease
    def record(*args, **kwargs):
        leases.append(kwargs['minutes'])
        return original(*args, **kwargs)
    monkeypatch.setattr(cluster_native,'SlurmLease',record)
    new = cluster_service(tmp_path/'new',task=load_task('s-204',version='expert-reference-v1'))
    old = cluster_service(tmp_path/'old',task=load_task('s-204'))
    assert leases == [35,8]
    assert new.max_seconds == 1800 and old.max_seconds == 300


def test_shell_prepare_works_without_inherited_pythonpath(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import json
    import yaml
    import campaign_config
    project = Path(__file__).resolve().parents[1]
    value = campaign_config.read(project/'experiments/science.yaml',project)
    value['execution']['prepared_parent'] = str(tmp_path/'prepared')
    config = tmp_path/'campaign.yaml'
    config.write_text(yaml.safe_dump(value))
    env = {k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}
    result = subprocess.run(['bash',str(project/'ci_checks/science.sh'),'prepare','--config',str(config)],
        env=env,cwd=tmp_path,capture_output=True,text=True,timeout=45)
    assert result.returncode == 0, result.stderr
    prepared = json.loads(result.stdout)
    assert prepared['model_requests_sent'] == 0
    assert Path(prepared['prepared'],'runtime/agentcfd_bench/__init__.py').is_file()


def test_native_preflight_imports_frozen_runtime_not_editable_cwd(tmp_path, monkeypatch):
    import os
    from pathlib import Path
    import campaign_config
    from launch_science_matrix import validate_runtime
    project = Path(__file__).resolve().parents[1]
    value = campaign_config.read(project/'experiments/science.yaml',project)
    value['execution']['prepared_parent'] = str(tmp_path/'prepared')
    prepared = campaign_config.prepare(value,project)
    runtime = Path(prepared['prepared'])/'runtime'
    # Reproduce the actual submit command, not a convenient parent-directory
    # test. The source project deliberately has no yaml-generated experiment.
    monkeypatch.chdir(project)
    env = {**os.environ,'PYTHONPATH':str(runtime)+':'+str(runtime/'ci_checks')}
    python = str((project/value['execution']['python']).absolute())
    ready = validate_runtime(python,env,runtime/'experiments/yaml-matrix.json')
    assert ready['tasks'] == 4 and ready['native_launches'] == 0
