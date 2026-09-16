"""Copy only runtime/task/doc/config sources into a new immutable-audit snapshot.

No runs, credentials, user homes, or previous agent sessions are copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def freeze(project, output, *, overlays=None, excluded=()):
    project, output = Path(project).resolve(), Path(output).resolve()
    names = ('agentcfd_bench', 'tasks', 'resources', 'experiments', 'ci_checks')
    if (project/'tests').is_dir():
        names += ('tests',)  # Release evidence binds the actual test source too.
    if (project/'task-drafts').is_dir():
        names += ('task-drafts',)  # Author-review test inputs; never agent mounted.
    if any(output.is_relative_to(project/name) for name in names):
        raise ValueError('Snapshot destination must not be inside a copied source directory')
    for relative in (overlays or {}):
        name = Path(relative)
        if name.is_absolute() or '..' in name.parts or name.parts[0] != 'experiments' or name.suffix != '.json':
            raise ValueError('Only new experiment JSON files may be compiled into a snapshot')
    excluded = tuple(Path(p).resolve() for p in excluded)
    ordinary = shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache', '.env*', '*.env', 'auth.json')
    def ignore(directory, entries):
        skipped = set(ordinary(directory, entries))
        for entry in entries:
            file = Path(directory)/entry
            if any(file.resolve() == p or file.resolve().is_relative_to(p) for p in excluded):
                skipped.add(entry)
            elif file.is_symlink():
                raise ValueError('Runtime source symlink requires explicit review: '+str(file))
        return skipped
    output.mkdir(parents=True, exist_ok=False)
    for name in names:
        shutil.copytree(project/name, output/name, ignore=ignore)
    for relative, value in (overlays or {}).items():
        name = Path(relative)
        with (output/name).open('x') as handle:
            json.dump(value, handle, sort_keys=True, ensure_ascii=False, indent=2)
    hashes = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(output.rglob('*')) if p.is_file()}
    with (output/'snapshot.json').open('x') as handle:
        json.dump({'source': str(project), 'files': hashes}, handle, sort_keys=True, indent=2)
    return {'snapshot': str(output), 'files': len(hashes)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.project, args.output)))
