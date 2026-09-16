import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace

import pytest

from agentcfd_bench.authoring.slurm_runner import validate_remote, SlurmRunner, WORK
from agentcfd_bench.authoring.slurm_job import command
from agentcfd_bench.authoring.slurm_transport import unpack_verified, SUBMIT
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.records.store import write_once


def remote():
    return {'host': 'sca2070', 'root': WORK + '/AgentCFD_Terminal_Bench/authoring/unit/operations',
            'partition': 'amd_256', 'runtime': '/readonly/runtime', 'python': '/readonly/python',
            'apptainer': '/readonly/apptainer', 'image': '/readonly/image'}


@pytest.mark.parametrize('path', ['/public3/home/sca2070', WORK, WORK + '/../other',
                                  WORK + '/AgentCFD_Terminal_Bench/a/../../elsewhere'])
def test_remote_scope_rejects_broad_or_escaping_paths(path):
    with pytest.raises(ValueError, match='Remote writes'):
        validate_remote({**remote(), 'root': path})


def test_container_does_not_mount_home_or_software_rw(tmp_path):
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    (runtime / 'manifest.json').write_bytes(b'{}')
    config = {**remote(), 'runtime': str(runtime), 'runtime_manifest_sha256': hashlib.sha256(b'{}').hexdigest()}
    args = command(tmp_path / 'op', {'remote': config, 'argv': ['icoFoam']})
    assert '--no-home' in args and '--containall' in args
    assert args[args.index('--network') + 1] == 'none'
    assert args[args.index('--no-mount') + 1] == 'hostfs,bind-paths,cwd'
    assert str(runtime) + '/content:/opt/foam:ro' in args
    (runtime / 'manifest.json').write_bytes(b'changed')
    with pytest.raises(RuntimeError, match='manifest changed'):
        command(tmp_path / 'op', {'remote': config, 'argv': ['icoFoam']})


def test_no_success_from_exit_before_artifact_collection(tmp_path):
    runner = SlurmRunner(tmp_path / 'native', Sandbox(), remote=remote())
    op = runner.root / 'r-0123456789abcdef'
    op.mkdir()
    write_once(op / 'exit.json', {'exit_code': 0, 'termination': 'exited'})
    assert runner.status(op.name)['lifecycle'] == 'interrupted'
    with pytest.raises(RuntimeError, match='terminal evidence'):
        runner.verify(op.name)


def archive(path, entries):
    with tarfile.open(path, 'w:gz') as tar:
        for name, data, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(data)
            if kind == tarfile.SYMTYPE:
                member.linkname = '/outside'
            tar.addfile(member, io.BytesIO(data))


def test_verified_transfer_and_corruption(tmp_path):
    entries = [('artifacts/case/0.5/U', b'field', tarfile.REGTYPE), ('stdout.log', b'end', tarfile.REGTYPE),
               ('stderr.log', b'', tarfile.REGTYPE)]
    result = {'artifacts': {'case/0.5/U': hashlib.sha256(b'field').hexdigest(),
                           '@stdout.log': hashlib.sha256(b'end').hexdigest(), '@stderr.log': hashlib.sha256(b'').hexdigest()}}
    path = tmp_path / 'data.tar.gz'
    archive(path, entries)
    unpack_verified(path, tmp_path / 'good', result)
    assert (tmp_path / 'good/artifacts/case/0.5/U').read_bytes() == b'field'
    result['artifacts']['case/0.5/U'] = '0' * 64
    with pytest.raises(ValueError, match='evidence changed'):
        unpack_verified(path, tmp_path / 'bad', result)


@pytest.mark.parametrize('entries', [
    [('../escape', b'x', tarfile.REGTYPE)],
    [('artifacts/link', b'', tarfile.SYMTYPE)],
    [('stdout.log', b'x', tarfile.REGTYPE), ('stdout.log', b'y', tarfile.REGTYPE)],
])
def test_unsafe_archive_rejected(tmp_path, entries):
    path = tmp_path / 'data.tar.gz'
    archive(path, entries)
    with pytest.raises(ValueError, match='Unsafe or duplicate'):
        unpack_verified(path, tmp_path / 'output', {'artifacts': {}})
    assert not (tmp_path / 'escape').exists()


def test_remote_submit_is_not_repeated_on_resume(tmp_path, monkeypatch):
    import subprocess
    root = tmp_path / 'r-0123456789abcdef'
    root.mkdir()
    write_once(root / 'spec.json', {'remote': remote()})
    calls = []
    def fake(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout='12345\n', stderr='')
    monkeypatch.setattr(subprocess, 'run', fake)
    monkeypatch.setattr(sys, 'argv', ['submit', str(root)])
    exec(SUBMIT, {})
    with pytest.raises(SystemExit):
        exec(SUBMIT, {})
    assert len(calls) == 1 and calls[0][0] == 'sbatch'
    assert '--no-requeue' in calls[0]


def test_unknown_submission_is_discovered_not_resent(tmp_path, monkeypatch):
    import subprocess
    root = tmp_path / 'r-0123456789abcdef'
    root.mkdir()
    write_once(root / 'spec.json', {'remote': remote()})
    write_once(root / 'submit-intent.json', {'job_name': 'acfd-a-0123456789abcdef'})
    calls = []
    def fake(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout='2468|acfd-a-0123456789abcdef\n', stderr='')
    monkeypatch.setattr(subprocess, 'run', fake)
    monkeypatch.setattr(sys, 'argv', ['submit', str(root)])
    exec(SUBMIT, {})
    assert {c[0] for c in calls} == {'squeue', 'sacct'}
    assert json.loads((root / 'slurm-job.json').read_text())['recovered'] is True


def test_unknown_missing_submission_is_not_recreated(tmp_path, monkeypatch):
    import subprocess
    root = tmp_path / 'r-0123456789abcdef'
    root.mkdir()
    write_once(root / 'spec.json', {'remote': remote()})
    write_once(root / 'submit-intent.json', {})
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout='', stderr=''))
    monkeypatch.setattr(sys, 'argv', ['submit', str(root)])
    with pytest.raises(RuntimeError, match='never resubmit'):
        exec(SUBMIT, {})
    assert not (root / 'slurm-job.json').exists()
