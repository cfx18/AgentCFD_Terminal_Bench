"""Freeze an explicit reviewed manifest; no solver/model/automatic registration.

--qualify imports and rechecks completed local native evidence only. Candidate
directories are immutable outputs, not silently added to the public registry.
"""
import argparse
import importlib
import json
from pathlib import Path
import re

import yaml

from agentcfd_bench.author_release import build_task
from agentcfd_bench.author_evidence import completed_operation
from agentcfd_bench.author_qualification import qualify
from agentcfd_bench.task_package import PROJECT, task_digest

MODULES = {'agentcfd_bench.free_mesh_flow', 'agentcfd_bench.free_mesh_shock',
           'agentcfd_bench.free_mesh_thermal', 'agentcfd_bench.free_mesh_buoyant'}


def freeze(config_path, output, *, project=PROJECT, qualify_completed=False):
    project, output = Path(project).resolve(), Path(output).resolve()
    config = yaml.safe_load(Path(config_path).read_text())
    rows = config['tasks']
    if (not isinstance(rows, list) or not rows or len({r['id'] for r in rows}) != len(rows)
            or any(not re.fullmatch(r's-[0-9]{3}', r['id']) or r['status'] not in ('candidate', 'review') for r in rows)):
        raise ValueError('Explicit unique candidate/review task registry required')
    output.mkdir(parents=True, exist_ok=False)
    (output/'config.snapshot.yaml').write_text(Path(config_path).read_text())
    summary = {'version': config['version'], 'registered': len(rows), 'model_calls': 0,
               'new_native_operations': 0, 'paid_ready': False, 'tasks': {}}
    registry = ['[dataset]', 'name = "science-free-mesh-author-candidate"', '']

    def local(relative):
        path = (project/relative).resolve()
        if not path.is_relative_to(project):
            raise ValueError('Author sources must be explicitly inside this project')
        return path

    for row in rows:
        name = row['id']
        status = {'status': row['status'], 'native_qualified': False,
                  'blockers': row.get('blockers', [])}
        if row['status'] == 'candidate':
            if row['acceptance_module'] not in MODULES:
                raise ValueError('Unreviewed acceptance module')
            module = importlib.import_module(row['acceptance_module'])
            materials = local(row['materials'])
            acceptance = module.create(materials)
            controls = {key: {**value, 'run_directory': str(local(value['run_directory']))}
                        for key, value in row['controls'].items()}
            native = completed_operation(controls['valid']['run_directory'])
            task = build_task(materials, output/name, version=config['version'],
                runtime=native['execution_task']['runtime'], groups=acceptance.check_groups,
                controls=controls, physical_error_checks=row['physical_error_checks'])
            status['task'] = task.binding
            if qualify_completed:
                result = qualify(output/'qualification'/name, task=task)
                status['native_qualified'] = result['passed']
                status['qualification_checks'] = result['checks']
            registry += ['[[tasks]]', f'id = "{name}"', 'status = "implemented"',
                         'digest = "'+task_digest(task.root)+'"', '']
        else:
            registry += ['[[tasks]]', f'id = "{name}"', 'status = "review"', '']
        summary['tasks'][name] = status
        print(json.dumps({'task_id': name, **status}, ensure_ascii=False), flush=True)
    (output/'dataset.toml').write_text('\n'.join(registry))
    (output/'author-review.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--qualify', action='store_true', help='Only import completed evidence; never rerun CFD')
    args = parser.parse_args()
    print(json.dumps(freeze(args.config, args.output, qualify_completed=args.qualify), ensure_ascii=False, indent=2))
