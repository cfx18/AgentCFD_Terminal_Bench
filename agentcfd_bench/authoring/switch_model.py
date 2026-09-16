"""Create a new authorized Sol author campaign, never relabel a Luna history."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from ..records.store import read, write_once
from .migration_gate import latest_controller, process_identity
from .slurm_runner import validate_remote
from .worker import validate_model


def adapt_prompt(text):
    identity = 'Use GPT-5.6 Luna through Codex; do not launch subagents.'
    if text.count(identity) != 1:
        raise ValueError('Expected one author model identity; review the prompt before switching')
    text = text.replace(identity, 'Use GPT-5.6 Sol through Codex; do not launch subagents.')
    old = ('The installed runtime has executables but not bin/tools/RunFunctions. The exact\n'
           'original helper is available in /input/source/OpenFOAM-v2306/bin/tools. For simple\n')
    if old in text:
        text = text.replace(old, 'The remote runtime includes executables and original bin/tools helpers.\n'
                            'Original helper source is also in /input/source/OpenFOAM-v2306/bin/tools. For simple\n')
    return text


def freeze(source_config, gate_dir, remote_config, output):
    source_config, gate_dir, output = map(lambda p: Path(p).resolve(), (source_config, gate_dir, output))
    source = read(source_config)
    if (source_config.parent / 'superseded.json').exists():
        raise ValueError('Source campaign already switched; do not create duplicate author attempts')
    gate, drain = read(gate_dir / 'gate-ready.json'), read(gate_dir / 'drained.json')
    if (Path(gate['source_config']).resolve() != source_config
            or drain['retired_controller_pid'] != latest_controller(source_config.parent)['pid']):
        raise ValueError('Drain receipt does not belong to the latest source controller')
    identity = process_identity(drain['retired_controller_pid'])
    if identity and identity['state'] != 'Z':
        raise RuntimeError('Source controller is still alive')
    if source['model'] != 'gpt-5.6-luna' or source['harness']['auth_home'] != '/root/.codex-experiment':
        raise ValueError('This switch is scoped to the approved experiment-account Luna campaign')
    remote = validate_remote(read(remote_config))
    previous_remote = source['remote']
    if (remote['runtime_manifest_sha256'] != previous_remote['runtime_manifest_sha256']
            or remote['pool']['root'] == previous_remote['pool']['root']):
        raise ValueError('Keep the qualified runtime but use a distinct shared pool')
    rows, selected = [], []
    for job in source.get('job_order', list(source['jobs'])):
        worker = Path(source['root']) / 'workers' / job
        result = read(worker / 'result.json') if (worker / 'result.json').exists() else None
        if result:
            harness = result.get('harness', {})
            errors = harness.get('errors', [])
            if any(error.get('upstream_result_known') is False for error in errors):
                raise ValueError('Unknown provider outcome needs review before a new attempt: ' + job)
            has_outputs = all((worker / 'agent/work' / name).is_file()
                              for name in source['jobs'][job]['expected_outputs'])
            mode = 'preserve_existing_material_for_review' if has_outputs else 'new_model_attempt'
        elif (worker / 'dispatch.json').exists():
            raise ValueError('Unresolved author dispatch: ' + job)
        else:
            mode = 'not_previously_started'
        if any((run / 'dispatch.json').exists() and not (run / 'exit.json').exists()
               for run in (worker / 'native').glob('r-*')):
            raise ValueError('Prior native operation is still unresolved: ' + job)
        rows.append({'job': job, 'mode': mode, 'previous_worker': str(worker),
                     'previous_model_calls': result.get('harness', {}).get('calls', 0) if result else 0})
        if mode != 'preserve_existing_material_for_review':
            selected.append(job)
    if not selected:
        raise ValueError('No unfinished author jobs to switch')
    output.mkdir(parents=True, exist_ok=False)
    jobs = {}
    for job in selected:
        old = source['jobs'][job]
        prompt = output / 'prompts' / (job + '.md')
        prompt.parent.mkdir(exist_ok=True)
        prompt.write_text(adapt_prompt(Path(old['prompt']).read_text()))
        jobs[job] = {**old, 'prompt': str(prompt)}
    switch = {'source_config': str(source_config), 'source_model': source['model'],
              'target_model': 'gpt-5.6-sol', 'rows': rows, 'counts': dict(Counter(r['mode'] for r in rows)),
              'user_confirmed': True, 'created': datetime.now(timezone.utc).isoformat(),
              'new_attempts_not_in_place_resumes': True,
              'prompt_changes': ['author model name', 'correct remote helper availability'],
              'science_and_budget_unchanged': True}
    config = {**source, 'root': str(output), 'model': 'gpt-5.6-sol', 'jobs': jobs, 'job_order': selected,
              'harness': {**source['harness'], 'reasoning_effort': 'high'},
              'remote': remote, 'attempt_count': len(jobs), 'model_switch': switch,
              'author_model_authorization': {'model': 'gpt-5.6-sol', 'reasoning_effort': 'high',
                   'auth_home': '/root/.codex-experiment', 'user_confirmed': True}}
    config.pop('after_campaign', None)
    config.pop('after_receipt', None)
    validate_model(config)
    write_once(output / 'registry.json', read(source_config.parent / 'registry.json'))
    write_once(output / 'model-switch.json', switch)
    write_once(output / 'campaign.json', config)
    write_once(source_config.parent / 'superseded.json', {
        'replacement': str(output / 'campaign.json'), 'reason': 'user_authorized_model_switch',
        'previous_receipts_preserved': True, 'created': switch['created']})
    return {'config': str(output / 'campaign.json'), 'model': config['model'],
            'counts': switch['counts'], 'selected': len(jobs), 'started': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-config', 'gate-dir', 'remote-config', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    print(json.dumps(freeze(**vars(parser.parse_args())), ensure_ascii=False, indent=2))
