"""Exercise the actual pytest producer, not just a handmade green XML."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from release_evidence import check, verify, summary, sidecar


@pytest.fixture
def execution(tmp_path):
    root = tmp_path/'runtime'
    (root/'tests').mkdir(parents=True)
    (root/'tests/test_sample.py').write_text('def test_sample():\n    assert 1 + 1 == 2\n')
    xml = tmp_path/'actual.xml'
    command = [sys.executable,'-B','-c',
        'import sys; sys.path.append("/usr/local/lib/python3.12/dist-packages"); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))',
        str(root/'tests'),'-q','-p','no:cacheprovider','-p','release_pytest','--release-root',str(root),
        '--junitxml='+str(xml)]
    result = subprocess.run(command, env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
        'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(Path(__file__).parent)},
        capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stdout+result.stderr
    return root,xml,command


def test_actual_execution_is_bound_but_unrelated_green_tests_cannot_release(execution):
    root,xml,_ = execution
    assert check(xml,root)['bound']
    result = verify([xml],root)
    assert not result['passed'] and result['missing_required']


@pytest.mark.parametrize('change',['source','xml','binding','during_execution','geometry'])
def test_changed_sources_or_receipts_cannot_release(execution, change):
    root,xml,_ = execution
    if change=='source': (root/'tests/test_sample.py').write_text('changed')
    elif change=='xml': xml.write_text(xml.read_text().replace('test_sample"','test_different"'))
    elif change=='geometry':
        (root/'task-drafts').mkdir()
        (root/'task-drafts/domain.stl').write_text('new geometry after tests')
    else:
        path = sidecar(xml); value = json.loads(path.read_text())
        if change=='binding': value['exit_code'] = 2
        else: value['sources_before'] = {'other':'different'}
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError): check(xml,root)


def test_old_evidence_is_not_overwritten_by_rerun(execution):
    root,xml,command = execution
    before = xml.read_bytes(),sidecar(xml).read_bytes()
    result = subprocess.run(command, env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
        'PYTHONPATH':str(Path(__file__).parent)},capture_output=True,text=True,timeout=30)
    assert result.returncode != 0 and 'new path' in result.stderr
    assert (xml.read_bytes(),sidecar(xml).read_bytes()) == before


def test_suite_counts_cannot_invent_executed_cases(tmp_path):
    path = tmp_path/'bad.xml'
    path.write_text('<testsuite tests="999" errors="0" failures="0" skipped="0"/>')
    with pytest.raises(ValueError,match='actual testcase'): summary(path)


def test_frozen_runtime_keeps_geometry_and_test_binding_inputs(tmp_path):
    from freeze_science_runtime import freeze
    from release_evidence import sources
    project=tmp_path/'project'
    for folder in ('agentcfd_bench','tasks','resources','experiments','ci_checks','tests','task-drafts'):
        (project/folder).mkdir(parents=True)
        (project/folder/'fixture.txt').write_text('offline fixture')
    target=tmp_path/'snapshot'
    freeze(project,target)
    assert sources(project)==sources(target)
    assert (target/'task-drafts/fixture.txt').read_text()=='offline fixture'
