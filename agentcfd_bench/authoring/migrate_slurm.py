"""Freeze only undispatched author jobs onto a qualified shared-node backend.

This prepares a new campaign, never reruns old jobs or alters their receipts.
The controller waits for the migration gate to retire the original controller.
"""
import argparse
import json
from pathlib import Path

from ..records.store import read, write_once
from .slurm_runner import validate_remote

OPERATIONS_NOTE = """

## Native execution location for this authoring campaign

Native operations run on one shared Slurm node, with at most ten independent
one-CPU job steps. Each operation keeps its own isolated /work and receipts.
Queueing is normal: keep polling the returned run_id; do not resubmit a command
merely because it is queued or running. This is serial OpenFOAM execution, not
MPI. Original OpenFOAM v2306 compiled tools and bin/tools helpers are available.
Only native computation moved; the scientific task and author budgets did not.
"""


def freeze(source_config, gate_dir, remote_config, qualification, output):
    source_config, gate_dir = Path(source_config).resolve(), Path(gate_dir).resolve()
    output = Path(output).resolve()
    source, gate = read(source_config), read(gate_dir / 'gate-ready.json')
    remote = validate_remote(read(remote_config))
    proof = read(qualification)
    if (proof.get('passed') is not True or proof.get('peak_parallel') != 10
            or proof.get('native', {}).get('passed') is not True
            or not remote.get('pool')
            or remote['runtime_manifest_sha256'] != proof['remote']['runtime_manifest_sha256']):
        raise ValueError('A passing shared-node/native qualification for this runtime is required')
    for key in ('allocation_cpus', 'max_parallel', 'step_cpus'):
        if remote['pool'][key] != proof['remote']['pool'][key]:
            raise ValueError('Production scheduling differs from qualification')
    if remote['pool']['root'] == proof['remote']['pool']['root']:
        raise ValueError('Prepare a fresh pool; do not reuse the stopped test allocation')
    if Path(gate['source_config']).resolve() != source_config:
        raise ValueError('Migration gate belongs to another campaign')
    moved, preserved = gate['unstarted_jobs'], gate['existing_jobs']
    if (not moved or len(set(moved + preserved)) != len(moved + preserved)
            or set(moved + preserved) != set(source['jobs'])):
        raise ValueError('Gate must account for every original job exactly once')
    if source['model'] != 'gpt-5.6-luna' or source['author_concurrency'] != 10:
        raise ValueError('Preserve the approved Luna/batch-ten author campaign')
    for job in moved:
        worker = Path(source['root']) / 'workers' / job
        if any((worker / name).exists() for name in ('dispatch.json', 'result.json', 'interrupted.json')):
            raise ValueError('Migration would replay an already dispatched author: ' + job)
    # A live gate holds the unstarted worker locks until its drain receipt exists.
    if not (gate_dir / 'drained.json').exists():
        from .migration_gate import process_identity
        identity = process_identity(gate['pid'])
        if (not identity or identity['state'] == 'Z' or str(gate_dir) not in identity['command']
                or 'agentcfd_bench.authoring.migration_gate' not in identity['command']):
            raise ValueError('No live migration gate and no drain receipt')
    output.mkdir(parents=True, exist_ok=False)
    jobs = {}
    order = [job for job in source.get('job_order', list(source['jobs'])) if job in moved]
    for job in order:
        old = source['jobs'][job]
        prompt = output / 'prompts' / (job + '.md')
        prompt.parent.mkdir(exist_ok=True)
        prompt.write_text(Path(old['prompt']).read_text() + OPERATIONS_NOTE)
        jobs[job] = {**old, 'prompt': str(prompt)}
    migration = {'source_config': str(source_config), 'gate': str(gate_dir),
                 'preserved_local_jobs': preserved, 'moved_jobs': order,
                 'original_attempt_count': len(source['jobs']),
                 'qualification': str(Path(qualification).resolve())}
    config = {**source, 'root': str(output), 'jobs': jobs, 'job_order': order,
              'attempt_count': len(jobs), 'native_backend': 'ssh-slurm', 'remote': remote,
              'after_receipt': str(gate_dir / 'drained.json'), 'migration': migration}
    config.pop('after_campaign', None)
    write_once(output / 'registry.json', read(Path(source['root']) / 'registry.json'))
    write_once(output / 'migration.json', migration)
    write_once(output / 'campaign.json', config)
    return {'config': str(output / 'campaign.json'), 'moved': len(jobs),
            'preserved': len(preserved), 'original_attempts': len(source['jobs']), 'started': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('source-config', 'gate-dir', 'remote-config', 'qualification', 'output'):
        parser.add_argument('--' + key, required=True, type=Path)
    print(json.dumps(freeze(**vars(parser.parse_args())), ensure_ascii=False, indent=2))
