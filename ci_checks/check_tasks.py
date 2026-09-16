"""Read-only release gate. Does not run models, native commands or task code."""
import json
import tomllib

from agentcfd_bench.task_package import TASKS, load_task


def check():
    registry = tomllib.loads((TASKS/'dataset.toml').read_text())
    identities = [item['id'] for item in registry['tasks']]
    if not identities or len(set(identities)) != len(identities):
        raise ValueError('Empty or duplicate registered task identities')
    for identity in identities:
        load_task(identity)
    unregistered = sorted(p.name for p in TASKS.iterdir()
                          if p.is_dir() and (p/'task.toml').is_file() and p.name not in identities)
    return {'registered': identities, 'unregistered': unregistered,
            'passed': True, 'executed_models': 0, 'executed_native_commands': 0}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, sort_keys=True))
