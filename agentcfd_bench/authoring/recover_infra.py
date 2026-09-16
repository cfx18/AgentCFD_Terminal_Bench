"""Freeze retry campaigns for author jobs with unknown infrastructure outcomes."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil

from ..records.store import read, write_once
from .control import retryable_infra_failure


def freeze(source_config, output, *, author_concurrency=None):
    source_config = Path(source_config).resolve()
    source = read(source_config)
    source_root = Path(source['root']).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(str(output))
    output.mkdir(parents=True)
    jobs, job_order, manifest = {}, [], {}
    for job_id in source.get('job_order', list(source['jobs'])):
        worker = source_root / 'workers' / job_id
        failure = retryable_infra_failure(worker)
        if not failure:
            continue
        prompt_source = Path(source['jobs'][job_id]['prompt'])
        prompt_target = output / 'prompts' / f'{job_id}.md'
        prompt_target.parent.mkdir(parents=True, exist_ok=True)
        prompt_target.write_text(prompt_source.read_text())
        jobs[job_id] = {**source['jobs'][job_id], 'prompt': str(prompt_target)}
        job_order.append(job_id)
        manifest[job_id] = {'source_worker': str(worker), 'failure': failure}
    if not jobs:
        raise ValueError('No retryable infrastructure failures found')
    width = source.get('author_concurrency', 1) if author_concurrency is None else author_concurrency
    if not isinstance(width, int) or width < 1:
        raise ValueError('author_concurrency must be a positive integer')
    config = {**source, 'root': str(output), 'jobs': jobs, 'job_order': job_order,
              'attempt_count': len(jobs), 'author_concurrency': min(width, len(jobs)),
              'recovery': {'kind': 'retryable_infrastructure_failure',
                           'source_config': str(source_config),
                           'created': datetime.now(timezone.utc).isoformat(),
                           'jobs': manifest}}
    if (source_root / 'registry.json').exists():
        shutil.copy2(source_root / 'registry.json', output / 'registry.json')
    write_once(output / 'infra-retry-manifest.json', config['recovery'])
    write_once(output / 'campaign.json', config)
    return {'config': str(output / 'campaign.json'), 'jobs': job_order, 'count': len(job_order)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_config', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--author-concurrency', type=int, default=None)
    args = parser.parse_args()
    print(__import__('json').dumps(
        freeze(args.source_config, args.output, author_concurrency=args.author_concurrency),
        ensure_ascii=False,
        indent=2,
    ))
