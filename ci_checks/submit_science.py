"""Manual front door. No model/cluster work on prepare, check or status.

The detached launcher and frozen matrix own execution and file monitoring.
This front door does not create a replacement agent loop or retry failed trials.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET

from release_evidence import verify as verify_tests

PROJECT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text())


def receipt(path):
    record = read_json(path)
    # Same canonical encoding as identity.fingerprint, without importing runtime.
    payload = json.dumps(record['payload'], sort_keys=True,
                         ensure_ascii=False, allow_nan=False).encode()
    if hashlib.sha256(payload).hexdigest() != record['hash']:
        raise ValueError('Receipt checksum mismatch: '+str(path))
    return record['payload']


def resolve(project, value, *, executable=False):
    path = Path(value)
    path = path if path.is_absolute() else project/path
    # Preserve the interpreter symlink: venv discovery depends on its path.
    return Path(os.path.abspath(path)) if executable else path.resolve()


def load_plan(config, project=PROJECT):
    project = Path(project).resolve()
    config = resolve(project, config)
    config_bytes = config.read_bytes()
    campaign = None
    if config.suffix.lower() in ('.yaml', '.yml'):
        from campaign_config import read, legacy_plan
        campaign = read(config, project, text=config_bytes.decode('utf-8'))
        value = legacy_plan(campaign, project)
    else:
        value = json.loads(config_bytes)
    required = {'version', 'python', 'runtime', 'manifest', 'probe', 'junit', 'model',
                'reasoning_effort', 'model_calls_per_task', 'authentication',
                'output_parent', 'release'}
    if not isinstance(value, dict) or set(value) != required or value['version'] != 'manual-science-launch-v1':
        raise ValueError('Expected exact manual-science-launch-v1 configuration')
    if (not isinstance(value['junit'], list) or not value['junit']
            or type(value['model_calls_per_task']) is not int or value['model_calls_per_task'] <= 0):
        raise ValueError('Nonempty test reports and positive call budget required')
    auth = value['authentication']
    if not isinstance(auth, dict):
        raise ValueError('Authentication configuration required')
    if auth.get('backend') == 'chatgpt-subscription':
        if set(auth) != {'backend', 'auth_home'} or not value['reasoning_effort']:
            raise ValueError('Subscription requires host auth_home and exact effort')
    elif auth.get('backend') == 'custom-api':
        if set(auth) != {'backend', 'env_file'} or value['reasoning_effort'] is not None:
            raise ValueError('Legacy custom API requires env_file, without subscription settings')
    else:
        raise ValueError('Unsupported authentication backend')
    release = value['release']
    if (not isinstance(release, dict) or set(release) != {'ready', 'audit_report', 'blockers'}
            or type(release['ready']) is not bool or not isinstance(release['blockers'], list)
            or any(not isinstance(x, str) for x in release['blockers'])):
        raise ValueError('Explicit reviewed release readiness required')
    paths = {key: resolve(project, value[key], executable=key == 'python')
             for key in ('python', 'runtime', 'manifest', 'probe', 'output_parent')}
    return {'config': config, 'config_bytes': config_bytes, 'project': project, 'value': value, 'campaign': campaign, **paths,
            'junit': [resolve(project, p) for p in value['junit']]}


def inspect(plan):
    value, runtime = plan['value'], plan['runtime']
    blockers, tasks, tests = [], [], []
    mode = 'live-probe'
    campaign = plan.get('campaign')
    selected_harness = campaign['harness']['name'] if campaign else plan.get('harness_name', 'codex')
    if campaign:
        mode = campaign['evidence'].get('interface_check', 'live-probe')
        from campaign_config import digest, compile_inputs, prepared_root, IMPLEMENTED_PROFILES
        tasks = list(campaign['tasks'])
        if campaign['instruction_profile'] not in IMPLEMENTED_PROFILES:
            blockers.append(campaign['instruction_profile']+' is review-only; geometry and mesh-independent acceptance are not released')
        try:
            prepared = read_json(prepared_root(campaign, plan['project'])/'configuration.json')
            if prepared != {'configuration': campaign, 'hash': digest(campaign)}:
                raise ValueError('YAML changed after prepare: use a new campaign name and prepare again')
            experiments, expected_matrix = compile_inputs(campaign, plan['project'])
            if read_json(plan['manifest']) != expected_matrix:
                raise ValueError('Prepared matrix differs from YAML')
            for relative, expected in experiments.items():
                if read_json(runtime/relative) != expected:
                    raise ValueError('Prepared experiment differs from YAML: '+relative)
            snapshot = read_json(runtime/'snapshot.json')
            for relative, expected in snapshot['files'].items():
                file = runtime/relative
                if file.is_symlink() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
                    raise ValueError('Frozen runtime content changed: '+relative)
            actual = {p.relative_to(runtime).as_posix() for p in runtime.rglob('*')
                      if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != 'snapshot.json'}
            if actual != set(snapshot['files']):
                raise ValueError('Frozen runtime file inventory changed')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            blockers.append('Prepare evidence: '+str(exc))
    if not value['release']['ready'] or value['release']['blockers']:
        blockers.extend(value['release']['blockers'] or ['Release has not been reviewed as ready'])
    if not plan['python'].is_file():
        blockers.append('Python interpreter missing: '+str(plan['python']))
    try:
        manifest = read_json(plan['manifest'])
        if (manifest.get('version') != 'explicit-science-matrix-v1'
                or manifest.get('provider_concurrency') != 1 or manifest.get('native_concurrency') != 1):
            raise ValueError('Existing runner requires explicit serial matrix')
        if manifest.get('harness', 'codex') != selected_harness:
            raise ValueError('Frozen matrix harness differs from selection')
        tasks = []
        for row in manifest['tasks']:
            experiment = read_json(runtime/'experiments'/row['experiment'])
            harness = experiment.get('harness', {})
            task_id = experiment['task']['id']
            if (experiment['model']['name'] != value['model']
                    or experiment['budget']['model_calls'] != value['model_calls_per_task']
                    or harness.get('backend', 'custom-api') != value['authentication']['backend']
                    or harness.get('reasoning_effort') != value['reasoning_effort']):
                raise ValueError('Model/backend/effort/budget differs from frozen task '+task_id)
            tasks.append(task_id)
        if not tasks or len(tasks) != len(set(tasks)):
            raise ValueError('Nonempty distinct task list required')
        spec = receipt(plan['probe']/'spec.json')
        result = receipt(plan['probe']/'result.json')
        from interface_evidence import validate as validate_interface
        mode = manifest.get('interface_check', 'live-probe')
        validate_interface(mode, spec, result)
        identity = spec['harness_identity']
        if (campaign or plan.get('archive')) and identity.get('name', 'codex') != selected_harness:
            raise ValueError('Interface probe belongs to another harness')
        if campaign or plan.get('archive'):
            for file, expected in identity.get('source_hashes', {}).items():
                if hashlib.sha256(Path(file).read_bytes()).hexdigest() != expected:
                    raise ValueError('Installed harness changed after probe: '+file)
        if (spec['model']['name'] != value['model']
                or identity.get('backend', 'custom-api') != value['authentication']['backend']
                or identity.get('reasoning_effort') != value['reasoning_effort']):
            raise ValueError('Interface probe belongs to another model/backend/effort')
        for name, expected in identity.get('bridge_source_hashes', {}).items():
            if hashlib.sha256((runtime/'agentcfd_bench'/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Runtime bridge changed after probe: '+name)
        if value['authentication']['backend'] == 'chatgpt-subscription' and not identity.get('bridge_source_hashes'):
            raise ValueError('Subscription probe lacks bridge-source binding')
        check = verify_tests(plan['junit'], runtime, subscription_xhigh=(
            value['authentication']['backend']=='chatgpt-subscription' and value['reasoning_effort']=='xhigh'))
        validate_interface(mode, spec, result, tests=check)
        tests = [{'path': str(path), **shard} for path, shard in zip(plan['junit'], check['shards'])]
        if not check['passed']:
            blockers.append('Source-bound test gate failed; missing required tests: '+', '.join(check['missing_required']))
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        blockers.append(str(exc))
    return {'ready': not blockers, 'model': value['model'], 'harness': selected_harness,
            'reasoning_effort': value['reasoning_effort'], 'tasks': tasks,
            'interface_check': mode,
            'model_calls_per_task': value['model_calls_per_task'],
            'blockers': blockers, 'tests': tests, 'model_requests_sent': 0,
            'note': 'Static check only: does not query live quota, run a solver, or qualify a changed release.'}


def run_paths(plan, name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', name):
        raise ValueError('Run name must be 1–80 letters/digits/_/- without a path')
    run = plan['output_parent']/name
    if (run/'run.json').is_file():
        from run_archive import paths
        return paths(run)
    return run, plan['output_parent']/(name+'-launch')


def launch_command(plan, name):
    if plan.get('archive'):
        from run_archive import paths
        run, launch = paths(plan['archive'])
    else:
        run, launch = run_paths(plan, name)
    command = [str(plan['python']), '-u', '-B', str(plan.get('launcher', plan['project']/'ci_checks/launch_science_matrix.py')),
        '--python', str(plan['python']), '--runtime', str(plan['runtime']),
        '--source-project', str(plan['project']), '--manifest', str(plan['manifest']),
        '--root', str(run), '--probe', str(plan['probe']), '--launch-dir', str(launch), '--allow-paid']
    for path in plan['junit']:
        command += ['--junit', str(path)]
    auth = plan['value']['authentication']
    key = 'auth_home' if auth['backend'] == 'chatgpt-subscription' else 'env_file'
    command += ['--'+key.replace('_', '-'), str(resolve(plan['project'], auth[key]))]
    return command


def show_status(run, launch):
    if (run.parent/'run.json').is_file() and run.name == 'results':
        record = read_json(run.parent/'run.json')
        print('Run:', record['run_id'])
        print('Created (UTC):', record['created_at'])
        print('Model / harness:', record['model'], '/', record['harness'])
        print('Configuration SHA256:', record['configuration_sha256'])
        print('Snapshot seal exists:', (run.parent/'archive.json').is_file())
        if (run.parent/'launcher-exit.json').is_file():
            print('Launcher exit (not test completion):', read_json(run.parent/'launcher-exit.json')['returncode'])
        if (run.parent/'launcher-interrupted.json').is_file():
            print('Launcher outcome unknown: inspect existing child receipts; do not blindly submit again.')
    scoreboard = run/'scoreboard.md'
    if scoreboard.is_file():
        print(scoreboard.read_text(), end='')
        print('Table updated:', datetime.fromtimestamp(scoreboard.stat().st_mtime, timezone.utc).isoformat())
    else:
        print('No scoreboard yet. Check the launch log; this does not imply that no process exists.')
    print('Log:', launch/'controller.log')
    print('Finished receipt exists:', (run/'campaign/finished.json').is_file())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'submit', 'status'])
    parser.add_argument('--config', default='experiments/science.yaml')
    parser.add_argument('--run-name', help='submit: optional label (<=32 chars); status: exact generated run ID or legacy name')
    parser.add_argument('--run-dir', help='status only: archive path, independent of the current YAML')
    parser.add_argument('--allow-paid', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.run_dir:
            if args.action != 'status' or args.run_name:
                raise ValueError('--run-dir is only for status and cannot be combined with --run-name')
            from run_archive import paths
            show_status(*paths(Path(args.run_dir).resolve()))
            return 0
        plan = load_plan(args.config)
        if args.action == 'prepare':
            if not plan.get('campaign'):
                raise ValueError('prepare requires a science-campaign-v1 YAML; legacy JSON is already compiled')
            from campaign_config import prepare
            print(json.dumps(prepare(plan['campaign'], plan['project']), ensure_ascii=False, indent=2))
            return 0
        if args.action == 'check':
            result = inspect(plan)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['ready'] else 2
        if args.action == 'status':
            if not args.run_name:
                raise ValueError('status requires --run-name or --run-dir')
            show_status(*run_paths(plan, args.run_name))
            return 0
        if not args.allow_paid:
            raise ValueError('submit requires explicit --allow-paid; check/status never dispatch models')
        result = inspect(plan)
        if not result['ready']:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2
        from run_archive import create, verify, paths, validate_label, write_once, utc
        if args.run_name:
            # Preserve the old guard against mistaking a known run for resume.
            run, launch = run_paths(plan, args.run_name)
            if run.exists() or launch.exists():
                raise ValueError('Existing run selected: status/recovery must use its original directory, not submit')
        validate_label(args.run_name)
        archived = create(plan, label=args.run_name)
        root = archived['archive']
        print('Run ID:', root.name, flush=True)
        print('Archive:', root, flush=True)
        verify(root)
        checked = inspect(archived)
        write_once(root/'readiness.json', checked)
        if not checked['ready']:
            print(json.dumps(checked, ensure_ascii=False, indent=2))
            return 2
        command = launch_command(archived, root.name)
        print('Launching:', shlex.join(command), flush=True)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONPATH': str(archived['runtime'])+':'+str(root/'snapshots/controller')}
        write_once(root/'launch-request.json', {'command': command, 'time': utc().isoformat()})
        try:
            with (root/'launcher.stdout.log').open('xb') as log:
                result = subprocess.run(command, env=env, cwd=plan['project'], check=False,
                    stdout=log, stderr=subprocess.STDOUT)
        except BaseException as exc:
            write_once(root/'launcher-interrupted.json', {'type': type(exc).__name__,
                'time': utc().isoformat(), 'outcome': 'unknown; inspect child receipts before any retry'})
            raise
        write_once(root/'launcher-exit.json', {'returncode': result.returncode, 'time': utc().isoformat(),
            'meaning': 'launcher exit only, not benchmark completion'})
        print((root/'launcher.stdout.log').read_text(errors='replace'), end='')
        run, launch = paths(root)
        if result.returncode == 0:
            print('Submitted. The detached local controller owns execution; no monitoring agent is needed.')
            print('Log:', launch/'controller.log')
            print('Table:', run/'scoreboard.md')
        else:
            print('Launcher failed; evidence retained in:', root)
        return result.returncode
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Blocked:', str(exc))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
