import json

import pytest

from agentcfd_bench.journal import NativeJournal
from freeze_science_runtime import freeze
from run_science_matrix import main, summary
from launch_science_matrix import interpreter, validate_runtime


def test_no_implicit_subscription_dispatch(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(['--project', str(tmp_path), '--source-project', str(tmp_path),
              '--manifest', 'missing', '--root', str(tmp_path/'run'), '--probe', 'missing'])
    assert exc.value.code == 2
    assert not (tmp_path/'run').exists()


def test_matrix_report_preserves_registered_denominator_and_is_repeatable(tmp_path):
    entries = [{'task': 'a'}, {'task': 'b'}, {'task': 'c'}]
    journal = NativeJournal(tmp_path/'campaign')
    journal.write('b', {'status': 'qualification_failed'})
    journal.write('c', {'status': 'infrastructure_error'})
    first = summary(tmp_path, entries)
    rendered = (tmp_path/'scoreboard.md').read_bytes()
    assert first == summary(tmp_path, entries)
    assert rendered == (tmp_path/'scoreboard.md').read_bytes()
    assert first['registered'] == 3 and first['passed'] == 0 and first['finished'] == 2
    assert len(json.loads((tmp_path/'scoreboard.json').read_text())['tasks']) == 3


def test_freeze_excludes_auth_old_runs_and_session_files(tmp_path):
    project = tmp_path/'project'
    project.mkdir()
    for name in ('agentcfd_bench', 'tasks', 'resources', 'experiments', 'ci_checks'):
        (project/name).mkdir()
        (project/name/'fixture.txt').write_text('public source')
    (project/'.env').write_text('SECRET')
    (project/'auth.json').write_text('SECRET')
    (project/'runs').mkdir()
    (project/'runs/history.json').write_text('PRIVATE HISTORY')
    result = freeze(project, tmp_path/'snapshot')
    assert result['files'] == 5
    assert not (tmp_path/'snapshot/auth.json').exists()
    assert not (tmp_path/'snapshot/runs').exists()
    assert 'SECRET' not in '\n'.join(p.read_text() for p in (tmp_path/'snapshot').rglob('*') if p.is_file())
    with pytest.raises(FileExistsError):
        freeze(project, tmp_path/'snapshot')


def test_launcher_preserves_virtualenv_symlink(tmp_path):
    binary = tmp_path/'venv/bin/python'
    binary.parent.mkdir(parents=True)
    binary.symlink_to('/usr/bin/python3')
    assert interpreter(binary) == str(binary)
    assert interpreter(binary) != str(binary.resolve())


def test_launcher_dependency_failure_happens_before_dispatch(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import launch_science_matrix
    calls = []
    def failed(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1, stdout='', stderr="ModuleNotFoundError: No module named 'harbor'")
    monkeypatch.setattr(launch_science_matrix.subprocess, 'run', failed)
    with pytest.raises(RuntimeError, match="No module named 'harbor'"):
        validate_runtime('/venv/bin/python', {}, tmp_path/'manifest.json')
    assert len(calls) == 1 and calls[0][0] == '/venv/bin/python'
