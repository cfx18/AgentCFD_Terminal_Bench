"""Watch authoring recovery campaigns and restart/retry infrastructure failures.

This is intentionally small: it does not grade or alter successful materials.
It only keeps supervisor processes alive and converts retryable infrastructure
failures with missing outputs into fresh low-concurrency recovery campaigns.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

from .control import launch, status
from .recover_infra import freeze


TERMINAL_WITHOUT_ACTION = {'completed', 'completed_with_interface_error'}
PROBLEM_TERMINALS = {'infra_error', 'interrupted'}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _log(path: Path, event: dict):
    event = {'time': _now(), **event}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')


def _supervisor_pids(config: Path):
    config = config.resolve()
    proc = subprocess.run(
        ['pgrep', '-af', f'agentcfd_bench.authoring.control supervise {config}'],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    pids = []
    for line in proc.stdout.splitlines():
        parts = line.split(maxsplit=1)
        if parts and parts[0].isdigit():
            pids.append(int(parts[0]))
    return pids


def _counts(report):
    counts = {}
    for worker in report.get('workers', {}).values():
        lifecycle = worker.get('lifecycle')
        counts[lifecycle] = counts.get(lifecycle, 0) + 1
    return counts


def _has_unfinished(report):
    return any(
        worker.get('lifecycle') in {'queued', 'running'}
        for worker in report.get('workers', {}).values()
    )


def _has_retryable_infra(report):
    return any(
        worker.get('lifecycle') in PROBLEM_TERMINALS
        and worker.get('infrastructure_error', {}).get('retryable')
        for worker in report.get('workers', {}).values()
    )


def _retryable_jobs(report):
    return tuple(sorted(
        job
        for job, worker in report.get('workers', {}).items()
        if worker.get('lifecycle') in PROBLEM_TERMINALS
        and worker.get('infrastructure_error', {}).get('retryable')
    ))


def watch(configs, *, log_path, poll_seconds, author_concurrency, max_auto_retries):
    active = [Path(config).resolve() for config in configs]
    auto_retries = 0
    seen = set()
    retried = set()
    _log(log_path, {
        'kind': 'watch_started',
        'configs': [str(path) for path in active],
        'poll_seconds': poll_seconds,
        'author_concurrency': author_concurrency,
        'max_auto_retries': max_auto_retries,
    })
    while True:
        any_unfinished = False
        for config in list(active):
            try:
                report = status(config)
            except Exception as exc:  # noqa: BLE001 - monitor must keep running.
                _log(log_path, {'kind': 'status_error', 'config': str(config), 'error': repr(exc)})
                continue
            counts = _counts(report)
            key = (str(config), json.dumps(counts, sort_keys=True))
            if key not in seen:
                seen.add(key)
                _log(log_path, {'kind': 'status', 'config': str(config), 'counts': counts})
            unfinished = _has_unfinished(report)
            any_unfinished = any_unfinished or unfinished
            pids = _supervisor_pids(config)
            if unfinished and not pids:
                try:
                    result = launch(config)
                    _log(log_path, {'kind': 'supervisor_restarted', 'config': str(config), 'result': result})
                except Exception as exc:  # noqa: BLE001
                    _log(log_path, {'kind': 'launch_error', 'config': str(config), 'error': repr(exc)})
            retryable_jobs = _retryable_jobs(report)
            retry_key = (str(config), retryable_jobs)
            if retryable_jobs and retry_key not in retried and auto_retries < max_auto_retries:
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                output = config.resolve().parent.parent / f'{stamp}-auto-infra-retry-low{author_concurrency}-r{auto_retries + 1}'
                try:
                    result = freeze(config, output, author_concurrency=author_concurrency)
                    active.append(Path(result['config']).resolve())
                    auto_retries += 1
                    retried.add(retry_key)
                    launch(Path(result['config']))
                    _log(log_path, {'kind': 'auto_retry_started', 'source': str(config), 'result': result})
                except ValueError:
                    pass
                except Exception as exc:  # noqa: BLE001
                    _log(log_path, {'kind': 'auto_retry_error', 'source': str(config), 'error': repr(exc)})
        if not any_unfinished:
            _log(log_path, {'kind': 'watch_completed', 'configs': [str(path) for path in active]})
            return
        time.sleep(poll_seconds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configs', nargs='+', type=Path)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--poll-seconds', type=int, default=60)
    parser.add_argument('--author-concurrency', type=int, default=1)
    parser.add_argument('--max-auto-retries', type=int, default=3)
    args = parser.parse_args()
    watch(
        args.configs,
        log_path=args.log,
        poll_seconds=args.poll_seconds,
        author_concurrency=args.author_concurrency,
        max_auto_retries=args.max_auto_retries,
    )


if __name__ == '__main__':
    main()
