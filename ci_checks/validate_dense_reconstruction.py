"""Sample accepted native references without rerunning their solvers.

Rebuild only a missing mesh from the original input, never evolve physical time.
Output is a new audit directory; original runs and GT remain read-only.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentcfd_bench.tasks.loader import Task
from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.grading.dense_native import sample_case
from agentcfd_bench.records.store import write_once


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    sandbox = Sandbox(foam_root=str(ROOT / 'environments/native-v2306/foam'), mpi='intelmpi')
    results = []
    for name in ('s-203', 's-204'):
        task = Task.load(ROOT / 'task-drafts/dense-observation-v1' / name)
        reference, _ = task.private()
        source = Path(reference['source']['run_directory'])
        inputs = json.loads((source / 'inputs.json').read_text())['payload']
        recorded = json.loads((source / 'result.json').read_text())['payload']['artifacts']
        work = output / name / 'reference-copy'
        work.mkdir(parents=True)
        for path, text in inputs.items():
            p = work / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
        for path, text in recorded.items():
            if path.startswith('mesh/'):
                path = 'constant/polyMesh/' + path.removeprefix('mesh/')
            elif not path.split('/')[0].replace('.', '', 1).isdigit():
                continue
            p = work / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
        mesh_commands = 0
        if not (work / 'constant/polyMesh/owner').exists():
            runner = Runner(output / name / 'mesh', sandbox, seconds=60)
            operation = runner.start(work, ['blockMesh'], kind='exec')
            while runner.status(operation['run_id'])['lifecycle'] == 'running': time.sleep(.05)
            directory, state = runner.verify(operation['run_id'])
            if not state['success']: raise RuntimeError('Reference mesh regeneration failed; inspect mesh logs')
            shutil.copytree(directory / 'artifacts', work, dirs_exist_ok=True)
            mesh_commands = 1
        result = sample_case(work, task.root / 'public', reference, sandbox, output / name / 'sampling')
        result.update(task=name, mesh_preprocessing_commands=mesh_commands, solver_runs=0, paid_calls=0)
        if any(row['maximum_absolute_error'] > 1e-8 for row in result['metrics'].values()):
            raise RuntimeError('Reference native replay does not reproduce exported observations: ' + name)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    write_once(output / 'validation.json', {'references': results, 'solver_runs': 0, 'paid_calls': 0})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
