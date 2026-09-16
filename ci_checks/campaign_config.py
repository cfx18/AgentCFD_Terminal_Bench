"""Compile a human-edited YAML campaign into the existing serial runner inputs.

Compilation is offline: no credentials are read, no client or solver is started.
The compiler never upgrades a reviewed task or qualifies a changed harness.
"""
import hashlib
import json
from pathlib import Path
import re
import tomllib

import yaml

VERSION = 'science-campaign-v1'
HARNESSES = ('codex', 'foamclaw', 'claude-code', 'kimi-code')
SUBSCRIPTION_MODELS = ('gpt-6-astra', 'gpt-5.6-sol')
MODELS = (*SUBSCRIPTION_MODELS, 'AWS-Claude-Fable-5', 'Kimi-K3', 'kimi-k3')
IMPLEMENTED_PROFILES = {'registered-v1': None, 'geometry-only-free-mesh-v1': 'free-mesh-v1',
                        'geometry-only-free-mesh-en-v2': 'expert-reference-v1',
                        'geometry-only-free-mesh-output-v1': 'expert-output-v1'}
PROFILES = (*IMPLEMENTED_PROFILES, 'physics-intent-draft-v1', 'geometry-only-free-mesh-draft-v1')


class StrictLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ValueError('YAML aliases are not supported; write explicit settings')
        return super().compose_node(parent, index)


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str) or key in result or key == '<<':
            raise ValueError('YAML keys must be unique strings; no merge keys')
        result[key] = loader.construct_object(value_node, deep=True)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ValueError(label + ': expected keys ' + keys)


def path(project, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Nonempty path string required')
    value = Path(name)
    return value if value.is_absolute() else project/value


def read(config, project, *, text=None):
    project = Path(project).resolve()
    try:
        value = yaml.load(Path(config).read_text() if text is None else text, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        raise ValueError('Invalid YAML: '+str(exc)) from exc
    exact(value, 'version name harness model tasks instruction_profile budget documentation execution authentication evidence release', 'campaign')
    if value['version'] != VERSION or not isinstance(value['name'], str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', value['name']):
        raise ValueError('Explicit campaign version and safe name required')
    exact(value['harness'], 'name backend reasoning_effort public_decision_log', 'harness')
    h = value['harness']
    exact(value['model'], 'name', 'model')
    if h['name'] not in HARNESSES or value['model']['name'] not in MODELS:
        raise ValueError('Unsupported harness/model; extend and test the allowlist explicitly')
    if type(h['public_decision_log']) is not bool:
        raise ValueError('public_decision_log must be boolean')
    if h['backend'] == 'chatgpt-subscription':
        if h['name'] != 'codex' or value['model']['name'] not in SUBSCRIPTION_MODELS or h['reasoning_effort'] not in ('low','medium','high','xhigh','max','ultra'):
            raise ValueError('Subscription selection requires codex + an explicit supported subscription model and effort')
        exact(value['authentication'], 'auth_home', 'subscription authentication')
    elif h['backend'] == 'custom-api':
        if value['model']['name'] == 'gpt-6-astra':
            raise ValueError('Astra tools require Responses; the legacy custom API bridge is Chat-only')
        if h['reasoning_effort'] is not None or h['public_decision_log']:
            raise ValueError('Current custom bridge requires null effort and public_decision_log: false')
        if (h['name'] != 'codex' and value['model']['name'] != 'Kimi-K3'
                and not (h['name'] == 'kimi-code' and value['model']['name'] == 'kimi-k3')):
            raise ValueError('Non-Codex bridges currently support only the explicit Kimi-K3 binding')
        exact(value['authentication'], 'env_file', 'custom API authentication')
    else:
        raise ValueError('Unknown authentication backend')
    for item in value['authentication'].values():
        path(project, item)  # Validate shape, never read credentials.
    if value['instruction_profile'] not in PROFILES:
        raise ValueError('Unknown instruction profile')
    tasks = value['tasks']
    registry = tomllib.loads((project/'tasks/dataset.toml').read_text())
    known = {row['id'] for row in registry['tasks']}
    if (not isinstance(tasks, list) or not tasks or any(not isinstance(t, str) or t not in known for t in tasks)
            or len(tasks) != len(set(tasks))):
        raise ValueError('tasks must be a nonempty, distinct list of registered task IDs')
    exact(value['budget'], 'model_calls native_seconds per_run_seconds request_seconds', 'budget')
    b = value['budget']
    ceiling = 1800 if value['instruction_profile'] in (
        'geometry-only-free-mesh-en-v2', 'geometry-only-free-mesh-output-v1') else 300
    if any(type(v) is not int or v <= 0 for v in b.values()) or b['per_run_seconds'] > min(ceiling, b['native_seconds']):
        raise ValueError(f'Positive integer budgets required; per_run_seconds <= min({ceiling}, native_seconds)')
    if value['documentation'] not in ('openfoam-v2306-reference-v1', 'none'):
        raise ValueError('Only the frozen OpenFOAM documentation bundle or none is supported; no internet mode')
    if value['instruction_profile'] != 'registered-v1' and value['documentation'] == 'none':
        raise ValueError('Physics-intent condition requires the approved OpenFOAM docs')
    exact(value['execution'], 'python prepared_parent output_parent provider_concurrency native_concurrency', 'execution')
    e = value['execution']
    if any(type(e[k]) is not int or e[k] != 1 for k in ('provider_concurrency', 'native_concurrency')):
        raise ValueError('This controller supports serial execution only; concurrency must be 1')
    for k in ('python', 'prepared_parent', 'output_parent'):
        path(project, e[k])
    evidence_keys = 'probe junit interface_check' if 'interface_check' in value['evidence'] else 'probe junit'
    exact(value['evidence'], evidence_keys, 'evidence')
    interface_check = value['evidence'].get('interface_check', 'live-probe')
    if interface_check not in ('live-probe', 'local-only') or (interface_check == 'local-only' and (
            h['name'] != 'codex' or h['backend'] != 'chatgpt-subscription' or h['reasoning_effort'] != 'xhigh')):
        raise ValueError('Local-only interface evidence is explicitly supported only for Codex subscription xhigh')
    path(project, value['evidence']['probe'])
    if not isinstance(value['evidence']['junit'], list) or not value['evidence']['junit']:
        raise ValueError('Nonempty test evidence list required')
    for item in value['evidence']['junit']:
        path(project, item)
    exact(value['release'], 'ready audit_report blockers', 'release')
    r = value['release']
    if type(r['ready']) is not bool or not isinstance(r['blockers'], list) or any(not isinstance(x, str) for x in r['blockers']):
        raise ValueError('Explicit boolean release readiness and blocker list required')
    path(project, r['audit_report'])
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def compile_inputs(value, project):
    """Pure generation. Task source/versions remain owned by the registry."""
    if value['instruction_profile'] not in IMPLEMENTED_PROFILES:
        raise ValueError(value['instruction_profile']+' is review-only: cannot compile it as registered-v1')
    from agentcfd_bench.task_package import load_task
    project = Path(project)
    catalog = json.loads((project/'experiments/task-catalog-v1.json').read_text())
    rows, experiments = [], {}
    for task_id in value['tasks']:
        version = IMPLEMENTED_PROFILES[value['instruction_profile']]
        # Never replace an unqualified new task with its old fixed-mesh namesake.
        if version is not None:
            package = load_task(task_id, version=version, tasks_root=project/'tasks')
            task = package.config['metadata']
        else:
            task = tomllib.loads((project/'tasks'/task_id/'task.toml').read_text())['metadata']
        row = catalog[task_id]
        experiment = {'version': 'science-from-scratch-v1',
            'task': {'id': task_id, 'version': task['version'], 'runtime': task['runtime']},
            'model': {'name': value['model']['name'], 'wire_api': 'responses' if value['harness']['backend'] == 'chatgpt-subscription' else 'chat'},
            'budget': dict(value['budget'])}
        if value['documentation'] != 'none':
            experiment['documentation'] = dict(json.loads((project/'experiments/sol-ultra-s-105-v1.json').read_text())['documentation'])
        if value['harness']['backend'] == 'chatgpt-subscription':
            experiment['harness'] = {k: v for k, v in value['harness'].items() if k != 'name'}
        name = 'yaml-generated-'+task_id+'.json'
        experiments['experiments/'+name] = experiment
        rows.append({'experiment': name, 'positive_source': row['positive_source'] if version is None else None})
    manifest = {'version': 'explicit-science-matrix-v1', 'provider_concurrency': 1,
        'native_concurrency': 1, 'harness': value['harness']['name'], 'tasks': rows}
    if value['evidence'].get('interface_check') == 'local-only':
        manifest['interface_check'] = 'local-only'
    return experiments, manifest


def prepared_root(value, project):
    return path(Path(project), value['execution']['prepared_parent']).resolve()/value['name']


def legacy_plan(value, project):
    root = prepared_root(value, project)
    return {'version': 'manual-science-launch-v1', 'python': value['execution']['python'],
        'runtime': str(root/'runtime'), 'manifest': str(root/'runtime/experiments/yaml-matrix.json'),
        'probe': value['evidence']['probe'], 'junit': value['evidence']['junit'],
        'model': value['model']['name'], 'reasoning_effort': value['harness']['reasoning_effort'],
        'model_calls_per_task': value['budget']['model_calls'],
        'authentication': {'backend': value['harness']['backend'], **value['authentication']},
        'output_parent': value['execution']['output_parent'], 'release': value['release']}


def prepare(value, project):
    # Do not present a short, incomplete prompt as a qualified new task release.
    if value['instruction_profile'] not in IMPLEMENTED_PROFILES:
        raise ValueError(value['instruction_profile']+' is review-only: geometry assets, mesh-independent acceptance and complete physical data are not released')
    from freeze_science_runtime import freeze
    root = prepared_root(value, project)
    experiments, manifest = compile_inputs(value, project)
    overlays = {**experiments, 'experiments/yaml-matrix.json': manifest}
    root.mkdir(parents=True, exist_ok=False)
    freeze(project, root/'runtime', overlays=overlays,
           excluded=[path(Path(project), item) for item in value['authentication'].values()])
    with (root/'configuration.json').open('x') as file:
        json.dump({'configuration': value, 'hash': digest(value)}, file, ensure_ascii=False, indent=2)
    return {'prepared': str(root), 'tasks': value['tasks'], 'harness': value['harness'],
        'model': value['model'], 'paid_ready': False, 'model_requests_sent': 0,
        'note': 'New snapshot only. Run check; a matching real interface probe and release review are still required.'}
