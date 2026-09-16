"""Offline, non-executing bridge setup. No SDK/client/legacy imports or secrets."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil


PROFILES = {
    'codex': {'entrypoint': 'agentcfd_bench.codex:factory', 'command': 'codex',
              'implementation': '@openai/codex', 'status': 'existing_bridge'},
    'foamclaw': {'entrypoint': None, 'command': None,
                 'implementation': 'foamclaw.core.react:ReActEngine', 'status': 'source_only'},
    'claude-code': {'entrypoint': None, 'command': 'claude',
                    'implementation': '@anthropic-ai/claude-code', 'status': 'bridge_missing'},
    'kimi-code': {'entrypoint': None, 'command': 'kimi',
                  'implementation': '@moonshot-ai/kimi-code', 'status': 'bridge_missing'},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n'


def snapshot(root, paths):
    result = {}
    for path in sorted(paths):
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
            raise ValueError('Source symlinks are not supported')
        if not path.is_file():
            raise ValueError('Required source file missing: ' + path.name)
        result[str(path.relative_to(root))] = digest(path)
    return result


def foamclaw_source(root):
    required = [root / p for p in ('foamclaw/core/react.py', 'foamclaw/core/llm.py',
                'foamclaw/core/memory.py', 'foamclaw/tools/registry.py', 'config/settings.py')]
    snapshot(root, required)
    tree = ast.parse(required[0].read_text())
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ReActEngine'), None)
    if cls is None:
        raise ValueError('ReActEngine not found in selected source')
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    constructor = methods.get('__init__')
    if constructor is None or 'run' not in methods:
        raise ValueError('ReActEngine constructor/run missing')
    args = {a.arg for a in constructor.args.args + constructor.args.kwonlyargs}
    if not {'llm', 'registry', 'memory'} <= args:
        raise ValueError('ReActEngine injection interface differs; review required')
    paths = list((root / 'foamclaw').rglob('*.py')) + list((root / 'config').rglob('*.py'))
    return snapshot(root, paths)


def configure(project, output, harness, model, wire_api, source=None):
    project, output = Path(project).resolve(), Path(output).absolute()
    if harness not in PROFILES or wire_api not in ('chat', 'responses') or not model.strip():
        raise ValueError('Explicit supported harness/model/wire-api required')
    if output.exists() or output.is_symlink():
        raise ValueError('Setup destination already exists; choose a new directory')
    required = ['agentcfd_bench/engine.py', 'agentcfd_bench/adapters/contract.py',
                'tasks/dataset.toml', 'experiments/science-from-scratch-rounds-v2.json']
    snapshot(project, [project / p for p in required])
    paths = list((project / 'agentcfd_bench').rglob('*.py'))
    paths += [project / p for p in required[2:]]
    # These are private source fingerprints, not qualification evidence.
    project_files = snapshot(project, paths)
    experiment = json.loads((project / required[-1]).read_text())
    experiment['model'] = {'name': model, 'wire_api': wire_api}
    source_root = Path(source).resolve() if source else None
    if harness == 'foamclaw' and source_root is None:
        raise ValueError('FoamClaw requires explicit --source; no implicit legacy imports')
    if harness != 'foamclaw' and source_root:
        raise ValueError('--source is only used by FoamClaw')
    source_files = foamclaw_source(source_root) if source_root else {}
    profile = PROFILES[harness]
    blockers = ['client_version_and_environment_not_verified',
                'current_setup_has_no_isolation_or_native_qualification_evidence',
                'harness_identity_not_bound_to_scheduler_state']
    if profile['entrypoint'] is None:
        blockers.insert(0, 'standalone_production_bridge_not_implemented')
    if harness == 'claude-code':
        blockers.append('anthropic_transport_not_supported_by_existing_codex_broker')
    if harness == 'kimi-code':
        blockers.append('must_distinguish_node_kimi_code_from_python_kimi_cli')
    config = {'version': 'harness-setup-v1', 'harness': harness, **profile,
        'project': str(project), 'source': str(source_root) if source_root else None,
        'project_files': project_files, 'source_files': source_files,
        'model': experiment['model'], 'comparison_track': 'unreviewed',
        'prompt_tools_memory_settings': 'must_freeze_before_comparison',
        'paid_ready': False, 'blockers': blockers}
    contents = {
        'harness.json': dump(config),
        'experiment.json': dump(experiment),
        '.env.example': ('# Host only. This is NOT loaded automatically. Never put keys in harness.json.\n'
                         '# SCIENCE_* is currently consumed only by the existing Codex paid CLI.\n'
                         'SCIENCE_API_BASE=\nSCIENCE_API_KEY=\n'),
    }
    lock = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in contents.items()}
    output.mkdir(parents=True, mode=0o700)
    for name, text in {**contents, 'setup-lock.json': dump(lock)}.items():
        with (output / name).open('x') as handle:
            handle.write(text)
    return doctor(output)


def doctor(setup):
    setup = Path(setup).resolve()
    lock = json.loads((setup / 'setup-lock.json').read_text())
    if set(lock) != {'harness.json', 'experiment.json', '.env.example'}:
        raise ValueError('Invalid setup lock')
    for name, expected in lock.items():
        path = setup / name
        if path.is_symlink() or digest(path) != expected:
            raise ValueError('Setup file changed: ' + name)
    config = json.loads((setup / 'harness.json').read_text())
    for directory, key in [('project', 'project_files'), ('source', 'source_files')]:
        if not config[directory]:
            continue
        root = Path(config[directory])
        files = config[key]
        for name in files:
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe source manifest path')
        if snapshot(root, [root / name for name in files]) != files:
            raise ValueError('Source changed since configuration; generate a new setup')
        if directory == 'project':
            current = {str(p.relative_to(root)) for p in (root / 'agentcfd_bench').rglob('*.py')}
            recorded = {p for p in files if p.startswith('agentcfd_bench/')}
            if current != recorded:
                raise ValueError('Project source set changed since configuration')
        if directory == 'source' and foamclaw_source(root) != files:
            raise ValueError('FoamClaw source set changed since configuration')
    command = config['command']
    return {'setup': str(setup), 'harness': config['harness'],
        'configuration_valid': True, 'status': config['status'],
        'executable_on_path': shutil.which(command) if command else None,
        'client_identity_verified': False, 'paid_ready': False,
        'blockers': config['blockers'], 'executed_models': 0, 'executed_native_commands': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    build = sub.add_parser('configure')
    build.add_argument('--project', required=True)
    build.add_argument('--harness', required=True, choices=PROFILES)
    build.add_argument('--model', required=True)
    build.add_argument('--wire-api', required=True, choices=['chat', 'responses'],
                       help='Candidate experiment protocol, not proof the selected client supports it')
    build.add_argument('--source')
    build.add_argument('--output', required=True)
    check = sub.add_parser('doctor')
    check.add_argument('--setup', required=True)
    args = vars(parser.parse_args())
    operation = args.pop('operation')
    try:
        result = configure(**args) if operation == 'configure' else doctor(**args)
    except (OSError, ValueError, SyntaxError, KeyError, TypeError) as exc:
        # Never print file contents, environment values or captured client output.
        parser.exit(2, 'Setup check failed: ' + str(exc) + '\n')
    print(dump(result), end='')


if __name__ == '__main__':
    main()
