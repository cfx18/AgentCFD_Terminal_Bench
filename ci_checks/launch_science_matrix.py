"""Checked, detached launch; preserve the venv interpreter instead of resolving its symlink."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from agentcfd_bench.journal import NativeJournal


def interpreter(path):
    # realpath/Path.resolve breaks Python virtualenv discovery: the executable
    # symlink's directory supplies pyvenv.cfg, not the target /usr/bin binary.
    return os.path.abspath(os.fspath(path))


def validate_runtime(python, env, manifest):
    code = ("import json,sys; from pathlib import Path; "
        "from agentcfd_bench.spec import load_experiment; "
        "from agentcfd_bench.task_package import load_task,PROJECT; "
        "from agentcfd_bench.runtime import cluster_service; "
        "m=json.loads(Path(sys.argv[1]).read_text()); "
        "[cluster_service(Path('/tmp/unused-native-preflight'),task=load_task("
        "e['task']['id'],version=e['task']['version'])) for r in m['tasks'] "
        "for e in [load_experiment(PROJECT/'experiments'/r['experiment'])]]; "
        "print(json.dumps({'python':sys.executable,'tasks':len(m['tasks']),'native_launches':0}))")
    # -c otherwise prepends cwd, which can silently import the editable source
    # instead of PYTHONPATH's frozen runtime when launched from the project.
    result = subprocess.run([python, '-P', '-B', '-c', code, str(manifest)], env=env,
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Host runtime import/construction failed before dispatch:\n'+result.stderr)
    return json.loads(result.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime', 'source-project', 'manifest', 'root', 'probe', 'launch-dir'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--junit', action='append', required=True)
    parser.add_argument('--python', default=sys.executable)
    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument('--auth-home')
    auth.add_argument('--env-file')
    parser.add_argument('--allow-paid', action='store_true')
    args = parser.parse_args(argv)
    if not args.allow_paid:
        parser.error('Explicit --allow-paid required')
    runtime, source, launch = (Path(v).resolve() for v in
        (args.runtime, args.source_project, args.launch_dir))
    python = interpreter(args.python)
    env = {**os.environ, 'PYTHONPATH': str(runtime)+':'+str(runtime/'ci_checks'),
           'PYTHONDONTWRITEBYTECODE': '1', 'AGENTCFD_HARNESS_RUNTIME': str(source/'.harness-runtime')}
    # Zero remote requests: fail before registering five misleading task errors.
    readiness = validate_runtime(python, env, Path(args.manifest).resolve())
    command = [python, '-u', '-B', str(runtime/'ci_checks/after_test_gate.py'), '--runtime', str(runtime)]
    manifest = json.loads(Path(args.manifest).read_text())
    for row in manifest['tasks']:
        experiment = json.loads((runtime/'experiments'/row['experiment']).read_text())
        harness = experiment.get('harness', {})
        if harness.get('backend')=='chatgpt-subscription' and harness.get('reasoning_effort')=='xhigh':
            command += ['--subscription-xhigh']
            break
    for path in args.junit:
        command += ['--junit', str(Path(path).resolve())]
    command += ['--wait-seconds', '1200', '--', python, '-u', '-B',
        str(runtime/'ci_checks/run_science_matrix.py'), '--project', str(runtime),
        '--source-project', str(source), '--manifest', str(Path(args.manifest).resolve()),
        '--root', str(Path(args.root).resolve()), '--probe', str(Path(args.probe).resolve()), '--allow-paid']
    command += ['--auth-home', str(Path(args.auth_home).resolve())] if args.auth_home else [
        '--env-file', str(Path(args.env_file).resolve())]
    launch.mkdir(parents=True, exist_ok=False)
    journal = NativeJournal(launch)
    journal.write('intent', {'command': command, 'readiness': readiness, 'log': str(launch/'controller.log')})
    with (launch/'controller.log').open('xb') as log:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, env=env, cwd=source.parent)
    journal.write('process', {'pid': child.pid, 'independent_session': True})
    print(json.dumps({'pid': child.pid, 'log': str(launch/'controller.log'), 'readiness': readiness}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
