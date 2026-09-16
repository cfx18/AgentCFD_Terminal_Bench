import copy
from pathlib import Path

import pytest

import campaign_config as campaign
import submit_science as manual

PROJECT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('profile',['physics-intent-draft-v1','geometry-only-free-mesh-draft-v1'])
def test_unreleased_profiles_cannot_compile_into_fixed_mesh_tasks(profile,tmp_path,monkeypatch):
    value = campaign.read(PROJECT/'experiments/science.yaml',PROJECT)
    value['instruction_profile'] = profile
    value['budget']['per_run_seconds'] = 300
    value['execution']['prepared_parent'] = str(tmp_path/'prepared')
    for function in (campaign.compile_inputs,campaign.prepare):
        with pytest.raises(ValueError,match='review-only'): function(value,PROJECT)
    assert not (tmp_path/'prepared').exists()
    import yaml
    value['release'] = {'ready':True,'audit_report':'not-qualification.md','blockers':[]}
    path=tmp_path/'force.yaml'; path.write_text(yaml.safe_dump(value))
    monkeypatch.setattr(manual.subprocess,'run',lambda *a,**k:pytest.fail('unreleased draft dispatched'))
    assert manual.main(['submit','--config',str(path),'--allow-paid'])==2


def test_default_selection_preserves_xhigh_no_child_profile_and_original_budget():
    value = campaign.read(PROJECT/'experiments/science.yaml',PROJECT)
    assert value['instruction_profile']=='geometry-only-free-mesh-output-v1'
    experiments, _ = campaign.compile_inputs(value, PROJECT)
    assert {row['task']['version'] for row in experiments.values()} == {'expert-output-v1'}
    assert value['harness']['reasoning_effort']=='xhigh'
    assert value['budget']['model_calls']==64
    assert set(value['budget'])=={'model_calls','native_seconds','per_run_seconds','request_seconds'}
    assert value['model']['name'] == 'gpt-6-astra'
    assert value['budget']['per_run_seconds'] == value['budget']['native_seconds'] == 1800
    assert value['evidence']['interface_check'] == 'local-only'
