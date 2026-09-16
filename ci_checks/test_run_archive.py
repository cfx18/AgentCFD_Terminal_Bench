"""Offline archive tests. Never dispatch a model, real harness, or solver."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import run_archive as archive
import submit_science as manual
from test_manual_submission import plan


def test_timestamp_config_fingerprint_uniqueness_and_private_root(plan):
    when = datetime(2026, 9, 15, 20, 30, 40, 123456, tzinfo=timezone(timedelta(hours=8)))
    one = archive.create(plan, now=when)
    two = archive.create(plan, now=when)
    a, b = one['archive'], two['archive']
    assert a != b and a.name.startswith('20260915T123040123456Z-')
    fingerprint = archive.fingerprint(plan['value'])
    assert fingerprint[:12] in a.name
    assert (a.stat().st_mode & 0o777) == 0o700
    assert archive.verify(a)['version'] == archive.VERSION
    assert json.loads((a/'run.json').read_text())['configuration_sha256'] == fingerprint
    assert not (a/'results').exists()  # Controller owns registration/launch.
    assert manual.inspect(one)['ready']


def test_same_timestamp_and_nonce_cannot_overwrite(plan):
    kwargs = dict(now=datetime(2026,9,15,tzinfo=timezone.utc), nonce='a'*8)
    first = archive.create(plan, **kwargs)
    record = (first['archive']/'archive.json').read_bytes()
    with pytest.raises(FileExistsError):
        archive.create(plan, **kwargs)
    assert (first['archive']/'archive.json').read_bytes() == record


def test_config_and_reference_bytes_are_independent_of_later_edits(plan):
    references = plan['project']/'references'
    references.mkdir()
    (references/'result.json').write_text('{"observed": 123}')
    matrix = json.loads(plan['manifest'].read_text())
    matrix['tasks'][0]['positive_source'] = 'references'
    plan['manifest'].write_text(json.dumps(matrix))
    original = plan['config'].read_bytes()
    archived = archive.create(plan)
    snap = archived['archive']/'snapshots'
    plan['config'].write_text('edited after load')
    (plan['runtime']/'experiments/a.json').write_text('{}')
    (references/'result.json').write_text('{}')
    assert (snap/'requested.json').read_bytes() == original
    assert json.loads((snap/'runtime/experiments/a.json').read_text())['task']['id'] == 's-test'
    relocated = json.loads(archived['manifest'].read_text())['tasks'][0]['positive_source']
    assert Path(relocated).is_relative_to(snap/'references')
    assert json.loads((Path(relocated)/'result.json').read_text()) == {'observed':123}
    assert archive.verify(archived['archive'])
    assert manual.inspect(archived)['ready']


def test_credential_files_and_login_directories_are_never_copied(plan):
    secret = plan['runtime']/'experiments/unusual-login'
    secret.mkdir()
    (secret/'login.dat').write_text('FAKE_SECRET')
    plan['value']['authentication']['auth_home'] = str(secret)
    for name in ('test.env','.env.production','auth.json'):
        (plan['runtime']/'experiments'/name).write_text('FAKE_SECRET')
    archived = archive.create(plan)
    snap = archived['archive']/'snapshots'
    assert not (snap/'runtime/experiments/unusual-login').exists()
    assert all(b'FAKE_SECRET' not in p.read_bytes() for p in snap.rglob('*') if p.is_file())


def test_snapshot_tamper_and_new_files_fail_integrity(plan):
    result = archive.create(plan)
    file = result['archive']/'snapshots/new.txt'
    file.write_text('unregistered')
    with pytest.raises(ValueError, match='changed'):
        archive.verify(result['archive'])


def test_run_identity_is_bound_by_the_seal(plan):
    root = archive.create(plan)['archive']
    metadata = json.loads((root/'run.json').read_text())
    metadata['model'] = 'not-the-requested-model'
    (root/'run.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='changed'):
        archive.verify(root)


def test_archive_rejects_symlink_and_retains_incomplete_intent(plan):
    (plan['runtime']/'escape').symlink_to('/does-not-exist')
    with pytest.raises(ValueError, match='symlink'):
        archive.create(plan)
    roots = list(plan['output_parent'].iterdir())
    assert len(roots) == 1 and (roots[0]/'run.json').is_file()
    assert (roots[0]/'archive-error.json').is_file()
    assert not (roots[0]/'archive.json').exists()
    assert not (roots[0]/'launch-request.json').exists()
    assert archive.paths(roots[0]) == (roots[0]/'results',roots[0]/'launch')


@pytest.mark.parametrize('label', ['../escape','/tmp/x','a'*33,''])
def test_bad_labels_do_not_create_directories(plan, label):
    with pytest.raises(ValueError):
        archive.create(plan, label=label)
    assert not plan['output_parent'].exists()


def test_refuses_recursive_output(plan):
    plan['output_parent'] = plan['runtime']/'nested'
    with pytest.raises(ValueError, match='inside'):
        archive.create(plan)
    assert not plan['output_parent'].exists()


def test_launch_uses_copied_runtime_configuration_and_evidence(plan, monkeypatch):
    monkeypatch.setattr(manual, 'load_plan', lambda _: plan)
    calls = []
    def fake(command, **kwargs):
        root = Path(command[command.index('--root')+1]).parent
        assert (root/'archive.json').is_file() and (root/'launch-request.json').is_file()
        assert Path(command[3]).is_relative_to(root/'snapshots')
        for key in ('--runtime','--manifest','--probe','--junit'):
            assert Path(command[command.index(key)+1]).is_relative_to(root/'snapshots')
        assert Path(command[command.index('--launch-dir')+1]) == root/'launch'
        assert str(root/'snapshots/runtime') in kwargs['env']['PYTHONPATH']
        kwargs['stdout'].write(b'fixture: local launch only\n')
        calls.append(command)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(manual.subprocess, 'run', fake)
    assert manual.main(['submit','--allow-paid']) == 0
    assert len(calls) == 1
    root = next(plan['output_parent'].iterdir())
    assert json.loads((root/'launcher-exit.json').read_text())['returncode'] == 0
    assert 'fixture' in (root/'launcher.stdout.log').read_text()
    # Same YAML explicitly submitted again is a separate, uniquely named run.
    assert manual.main(['submit','--allow-paid']) == 0
    assert len(list(plan['output_parent'].iterdir())) == 2


def test_launch_failure_is_recorded_without_automatic_retry(plan, monkeypatch):
    monkeypatch.setattr(manual, 'load_plan', lambda _: plan)
    calls = []
    def failed(*a, **kw):
        calls.append(a)
        kw['stdout'].write(b'fixture runtime import failure\n')
        return SimpleNamespace(returncode=2)
    monkeypatch.setattr(manual.subprocess, 'run', failed)
    assert manual.main(['submit','--allow-paid']) == 2
    root = next(plan['output_parent'].iterdir())
    assert len(calls) == 1 and (root/'archive.json').exists()
    assert json.loads((root/'launcher-exit.json').read_text())['returncode'] == 2
    assert not (root/'results/campaign/finished.json').exists()


def test_unknown_launch_outcome_keeps_intent_not_fabricated_exit(plan, monkeypatch):
    monkeypatch.setattr(manual, 'load_plan', lambda _: plan)
    def interrupted(*a, **kw):
        raise KeyboardInterrupt()
    monkeypatch.setattr(manual.subprocess, 'run', interrupted)
    with pytest.raises(KeyboardInterrupt):
        manual.main(['submit','--allow-paid'])
    root = next(plan['output_parent'].iterdir())
    assert (root/'launch-request.json').exists() and (root/'launcher-interrupted.json').exists()
    assert not (root/'launcher-exit.json').exists()


def test_status_by_archive_path_ignores_current_yaml_and_does_not_mutate(plan, monkeypatch):
    root = archive.create(plan)['archive']
    (root/'results').mkdir()
    (root/'results/scoreboard.md').write_text('# Saved result\n')
    before = {str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    monkeypatch.setattr(manual, 'load_plan', lambda _: pytest.fail('status must not read current config'))
    monkeypatch.setattr(manual.subprocess, 'run', lambda *a, **k: pytest.fail('status dispatched'))
    assert manual.main(['status','--run-dir',str(root)]) == 0
    assert {str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()} == before
    assert manual.run_paths(plan, root.name) == (root/'results',root/'launch')
    assert manual.run_paths(plan, 'old') == (plan['output_parent']/'old',plan['output_parent']/'old-launch')


def test_yaml_prepare_and_archive_keep_comments_tasks_and_budget(tmp_path):
    import yaml
    import campaign_config as campaign
    from agentcfd_bench.journal import NativeJournal
    project = manual.PROJECT
    value = campaign.read(project/'experiments/science.yaml', project)
    value.update(name='archive-fixture',tasks=['s-001'],instruction_profile='registered-v1')
    value['budget']['per_run_seconds'] = 300  # This fixture exercises the legacy release.
    value['harness'] = dict(name='foamclaw',backend='custom-api',reasoning_effort=None,public_decision_log=False)
    value['model'] = {'name':'Kimi-K3'}
    value['authentication'] = {'env_file':str(tmp_path/'not-read.env')}
    value['budget']['model_calls'] = 19
    value['execution'].update(prepared_parent=str(tmp_path/'prepared'),output_parent=str(tmp_path/'runs'))
    value['evidence'] = {'probe':str(tmp_path/'probe'),'junit':[str(tmp_path/'tests.xml')]}
    value['release'] = dict(ready=True,blockers=[],audit_report='fixture-not-release.md')
    probe = NativeJournal(tmp_path/'probe')
    probe.write('spec', {'model':{'name':'Kimi-K3','wire_api':'chat'}, 'harness_identity':{'name':'foamclaw'}})
    probe.write('result', {'passed':True,'benchmark_score':False})
    file = tmp_path/'requested.yaml'
    file.write_text('# 保留原始注释\n'+yaml.safe_dump(value,allow_unicode=True))
    campaign.prepare(value, project)
    plan = manual.load_plan(file)
    from test_manual_submission import fake_test_evidence
    fake_test_evidence(plan['runtime'], tmp_path/'tests.xml')
    assert manual.inspect(plan)['ready']
    result = archive.create(plan)
    assert manual.inspect(result)['ready']
    root = result['archive']
    assert (root/'snapshots/requested.yaml').read_bytes() == file.read_bytes()
    experiment = json.loads((root/'snapshots/runtime/experiments/yaml-generated-s-001.json').read_text())
    assert experiment['budget']['model_calls'] == 19
    assert json.loads((root/'run.json').read_text())['harness'] == 'foamclaw'
    assert (root/'snapshots/preparation.json').is_file()
    assert archive.verify(root)


def test_source_change_after_prepare_cannot_be_sealed(plan):
    hashes = archive.inventory(plan['runtime'])
    archive.write_once(plan['runtime']/'snapshot.json', {'files':hashes})
    (plan['runtime']/'experiments/a.json').write_text('{}')
    with pytest.raises(ValueError, match='preparation fingerprint'):
        archive.create(plan)
    root = next(plan['output_parent'].iterdir())
    assert (root/'archive-error.json').exists() and not (root/'archive.json').exists()


def test_archived_reference_receipts_still_validate_at_the_new_path(tmp_path):
    from agentcfd_bench.reference_prepare import ImportedReferenceTask
    from agentcfd_bench.task_package import load_task
    from agentcfd_bench.tutorial_baseline import audit_preparation
    source = manual.PROJECT/'runs/tutorial-reference-preparation-001/s-105'
    target = tmp_path/'reference'
    archive.copy_tree(source, target, ())
    task = ImportedReferenceTask(load_task('s-105'))
    # Read-only validation of archived existing solver evidence. No new solve.
    assert audit_preparation(task, target) == audit_preparation(task, source)
