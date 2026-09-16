"""Host-only, per-launch archive. No credentials, model calls, or solver work.

An archive is sealed before launch; generated results are written separately.
Directory creation is exclusive. An incomplete archive is never auto-retried.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import uuid

VERSION = 'science-run-archive-v1'


def utc():
    return datetime.now(timezone.utc)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()


def fingerprint(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def write_once(path, value):
    """Persist an observed event before inspecting any subsequent outputs."""
    path = Path(path)
    with path.open('xb') as file:
        file.write(encoded(value)+b'\n')
        file.flush()
        os.fsync(file.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda: file.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def ignored(path, excluded):
    return (path.name == 'auth.json' or path.name.startswith('.env') or path.suffix == '.env'
        or any(path.resolve() == p or path.resolve().is_relative_to(p) for p in excluded)
        or '__pycache__' in path.parts or path.suffix == '.pyc' or '.pytest_cache' in path.parts)


def inventory(root, excluded=()):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Archive source must be a real directory: '+str(root))
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            path = Path(directory)/name
            if ignored(path, excluded):
                dirs.remove(name)
            elif path.is_symlink():
                raise ValueError('Archive refuses symlink: '+str(path))
        for name in files:
            path = Path(directory)/name
            if ignored(path, excluded):
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError('Archive refuses non-regular file: '+str(path))
            result[path.relative_to(root).as_posix()] = file_hash(path)
    return result


def copy_tree(source, destination, excluded):
    """Independent bytes, not links to editable experiment/reference inputs."""
    source, destination = Path(source), Path(destination)
    if destination.resolve().is_relative_to(source.resolve()):
        raise ValueError('Archive destination must not be inside its source')
    expected = inventory(source, excluded)
    destination.mkdir(parents=True, exist_ok=False)
    for relative in expected:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/relative, target, follow_symlinks=False)
    if inventory(destination) != expected or inventory(source, excluded) != expected:
        raise ValueError('Source changed while archiving: '+str(source))
    return expected


def copy_file(source, destination):
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_file():
        raise ValueError('Archive requires a regular file: '+str(source))
    expected = file_hash(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as src, destination.open('xb') as dst:
        shutil.copyfileobj(src, dst)
        dst.flush()
        os.fsync(dst.fileno())
    if file_hash(destination) != expected or file_hash(source) != expected:
        raise ValueError('Source changed while archiving: '+str(source))


def validate_label(label):
    if label is not None and (not isinstance(label, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}', label)):
        raise ValueError('Optional launch label must be 1–32 letters/digits/_/- without a path')


def create(plan, *, label=None, now=None, nonce=None):
    """Caller must pass readiness checks first. Returns paths for actual launch."""
    validate_label(label)
    when = now or utc()
    if when.tzinfo is None:
        raise ValueError('Archive timestamp must have an explicit timezone')
    when = when.astimezone(timezone.utc)
    configuration = plan.get('campaign') or plan['value']
    config_hash = fingerprint(configuration)
    suffix = nonce if nonce is not None else uuid.uuid4().hex[:8]
    if not re.fullmatch(r'[a-f0-9]{8}', suffix):
        raise ValueError('Archive nonce must contain eight hexadecimal characters')
    run_id = (label+'-' if label else '') + when.strftime('%Y%m%dT%H%M%S%fZ')+'-'+config_hash[:12]+'-'+suffix
    root = plan['output_parent']/run_id
    # Never nest a copy in its input, including a misconfigured output_parent.
    sources = [plan['runtime'], plan['probe']]
    matrix = json.loads(plan['manifest'].read_text())
    references = []
    for row in matrix['tasks']:
        source = row.get('positive_source')
        references.append((plan['project']/source).resolve() if source else None)
    sources += [s for s in references if s]
    if any(root.resolve().is_relative_to(Path(s).resolve()) for s in sources):
        raise ValueError('Run output cannot be placed inside a snapshot source')
    auth = plan['value']['authentication']
    excluded = tuple((plan['project']/v).resolve() for k, v in auth.items() if k != 'backend')
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(mode=0o700, exist_ok=False)
    write_once(root/'run.json', {'version': VERSION, 'run_id': run_id,
        'created_at': when.isoformat(), 'configuration_sha256': config_hash,
        'label': label, 'model': plan['value']['model'],
        'harness': (plan.get('campaign') or {}).get('harness', {}).get('name', matrix.get('harness', 'codex')),
        'layout': {'snapshots': 'snapshots', 'results': 'results', 'launch': 'launch'},
        'source_config': str(plan['config']), 'meaning': 'archive intent, not proof of a launched or completed test'})
    try:
        snap = root/'snapshots'
        snap.mkdir()
        raw = plan.get('config_bytes')
        if raw is None:
            raw = plan['config'].read_bytes()
        with (snap/('requested'+plan['config'].suffix)).open('xb') as file:
            file.write(raw)
        write_once(snap/'effective.json', configuration)
        write_once(snap/'source-matrix.json', matrix)
        copy_tree(plan['runtime'], snap/'runtime', excluded)
        frozen_index = snap/'runtime/snapshot.json'
        if frozen_index.is_file():
            expected = json.loads(frozen_index.read_text())['files']
            actual = inventory(snap/'runtime')
            actual.pop('snapshot.json')
            if actual != expected:
                raise ValueError('Copied runtime no longer matches its preparation fingerprint')
        if plan.get('campaign'):
            from campaign_config import compile_inputs
            expected, expected_matrix = compile_inputs(plan['campaign'], plan['project'])
            if expected_matrix != matrix or any(json.loads((snap/'runtime'/key).read_text()) != value
                                                 for key, value in expected.items()):
                raise ValueError('Copied experiments differ from requested YAML')
        copy_file(plan['project']/'ci_checks/launch_science_matrix.py', snap/'controller/launch_science_matrix.py')
        for name in ('spec.json', 'result.json'):
            copy_file(plan['probe']/name, snap/'probe'/name)
        tests = []
        for index, source in enumerate(plan['junit']):
            target = snap/'tests'/f'{index:03d}-{source.name}'
            copy_file(source, target)
            from release_evidence import sidecar
            copy_file(sidecar(source), sidecar(target))
            tests.append(target)
        if plan.get('campaign'):
            from campaign_config import prepared_root
            copy_file(prepared_root(plan['campaign'], plan['project'])/'configuration.json', snap/'preparation.json')
        audit = (plan['project']/plan['value']['release']['audit_report'])
        if audit.is_file():
            copy_file(audit, snap/('release-audit'+audit.suffix))
        relocated = json.loads(json.dumps(matrix))
        reused = {}
        for index, (row, source) in enumerate(zip(relocated['tasks'], references)):
            if source is not None:
                if source not in reused:
                    target = snap/'references'/f'{index:03d}'
                    copy_tree(source, target, excluded)
                    reused[source] = target
                row['positive_source'] = str(reused[source])
        write_once(snap/'matrix.json', relocated)
        archived = {**plan, 'archive': root, 'campaign': None,
            'harness_name': matrix.get('harness', 'codex'),
            'runtime': snap/'runtime', 'manifest': snap/'matrix.json',
            'probe': snap/'probe', 'junit': tests,
            'launcher': snap/'controller/launch_science_matrix.py'}
        write_once(snap/'execution.json', {'version': VERSION,
            'python': str(plan['python']), 'source_project': str(plan['project']),
            'runtime': 'snapshots/runtime', 'manifest': 'snapshots/matrix.json',
            'probe': 'snapshots/probe', 'junit': [str(p.relative_to(root)) for p in tests],
            'authentication': auth, 'results': 'results', 'launch': 'launch',
            'external_dependencies': 'Host Python/client binaries, login or env file, cluster and OpenFOAM image are not copied'})
        hashes = inventory(snap)
        write_once(root/'archive.json', {'version': VERSION, 'files': hashes,
            'snapshot_sha256': fingerprint(hashes), 'run_metadata_sha256': file_hash(root/'run.json'),
            'sealed_at': utc().isoformat()})
        return archived
    except BaseException as exc:
        write_once(root/'archive-error.json', {'type': type(exc).__name__, 'reason': str(exc),
            'time': utc().isoformat(), 'model_requests_sent': 0})
        if isinstance(exc, Exception):
            raise ValueError('Archive failed; retained at '+str(root)+': '+str(exc)) from exc
        raise


def verify(root):
    root = Path(root)
    record = json.loads((root/'archive.json').read_text())
    if (record['version'] != VERSION or fingerprint(record['files']) != record['snapshot_sha256']
            or file_hash(root/'run.json') != record['run_metadata_sha256']
            or inventory(root/'snapshots') != record['files']):
        raise ValueError('Run snapshot changed or is incomplete')
    return record


def paths(root):
    """Read-only lookup; incomplete archives still retain their intended layout."""
    root = Path(root)
    record = json.loads((root/'run.json').read_text())
    if record.get('version') != VERSION or record.get('layout') != {
            'snapshots': 'snapshots', 'results': 'results', 'launch': 'launch'}:
        raise ValueError('Unrecognized archive layout')
    return root/'results', root/'launch'
