"""Explicit, qualified single-task runner using the real shared Codex bridge.

Run with PYTHONPATH pointing to a frozen runtime. This is a host controller,
not code mounted into the agent. Unknown provider outcomes are never retried.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
import time

from agentcfd_bench.journal import NativeJournal
from agentcfd_bench.runtime import Pending


def emit(kind, **details):
    print(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                      'kind': kind, **details}, ensure_ascii=False), flush=True)


class ObserveNative:
    """Observe the same journalled operation; never allocate a replacement run."""
    def __init__(self, service, *, wait=time.sleep):
        self.service, self.wait = service, wait
        self.task_identity = service.task_identity

    def execute(self, run_id, files, seconds):
        previous = None
        # A lost receipt or vanished allocation must not leave a controller
        # polling forever. Exhaustion interrupts; the same run remains resumable.
        observations = max(3, int(seconds / 15) + 20)
        for observation in range(observations):
            try:
                return self.service.execute(run_id, files, seconds)
            except RuntimeError as exc:
                if not isinstance(exc, Pending) and '|PENDING|' not in str(exc):
                    raise
                # No new model call. NativeService uses the existing launch,
                # exit and result receipts when it observes this same run ID.
                reason = str(exc)
                if reason != previous:
                    emit('observing_existing_native_operation', run_id=run_id, reason=reason)
                    previous = reason
                self.wait(15)
        raise Pending(f'native_observation_window_exhausted after {observations} observations; '
                      'inspect existing receipts, do not submit a replacement job')


def watch(root, stop):
    from agentcfd_bench.reporting import report
    previous = None
    while not stop.wait(15):
        if not (root/'state.sqlite').exists():
            continue
        try:
            data = report(root, write=True)
            row = {k:data[k] for k in ('task', 'model', 'lifecycle', 'phase', 'verdict',
                   'reason', 'model_calls', 'run_submissions', 'report_failures')}
            if row != previous:
                emit('progress', **row)
                previous = row
        except Exception as exc:
            emit('monitor_error', type=type(exc).__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--harness', choices=['codex', 'foamclaw', 'claude-code', 'kimi-code'], default='codex')
    parser.add_argument('--root', required=True)
    parser.add_argument('--qualification', required=True)
    parser.add_argument('--env-file')
    parser.add_argument('--auth-home', help='Host-only Codex login directory, subscription backend only')
    parser.add_argument('--legacy-root', required=True)
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--launch-id', help='Matrix-generated immutable launch identity')
    args = parser.parse_args(argv)
    if args.launch_id and not re.fullmatch('[0-9a-f]{32}', args.launch_id):
        parser.error('launch-id must be a 32-character lowercase hex UUID')
    if not args.allow_paid:
        parser.error('Explicit --allow-paid required')
    from agentcfd_bench.spec import load_experiment, prepare
    from agentcfd_bench.task_package import load_task
    from agentcfd_bench.qualification import require_qualified, protocol_identity
    experiment = load_experiment(args.experiment)
    prepare(experiment)
    task = load_task(experiment['task']['id'], version=experiment['task']['version'])
    require_qualified(args.qualification, task=task)  # Before any API work.
    root = Path(args.root).resolve()
    if args.resume:
        if not (root/'state.sqlite').is_file():
            parser.error('No existing checkpoint to resume')
    else:
        root.mkdir(parents=True, exist_ok=False)
    harness = experiment.get('harness', {})
    if harness.get('backend') == 'chatgpt-subscription' and args.harness != 'codex':
        parser.error('Subscription authentication requires the Codex harness')
    extra = {}
    if harness.get('backend') == 'chatgpt-subscription':
        if args.env_file:
            parser.error('Subscription mode must not load custom API credentials')
        from agentcfd_bench.adapters.subscription_auth import SubscriptionAuth
        endpoint = key = None
        extra = {**harness, 'auth': SubscriptionAuth(args.auth_home)}
    else:
        if not args.env_file or args.auth_home:
            parser.error('Custom API mode requires --env-file and does not use --auth-home')
        from dotenv import dotenv_values
        values = dotenv_values(args.env_file)
        endpoint = values.get('SCIENCE_API_BASE') or values.get('OPENAI_BASE_URL')
        key = values.get('SCIENCE_API_KEY') or values.get('OPENAI_API_KEY')
        if not endpoint or not key:
            parser.error('Explicit provider URL and credential required')
    from agentcfd_bench.documentation import load
    from agentcfd_bench.smoke.agent import factory
    from agentcfd_bench.runtime import cluster_service
    from agentcfd_bench.engine import run
    factory_ = factory(root/'agent', args.harness, endpoint=endpoint, credential=key,
        legacy=Path(args.legacy_root).resolve(), seconds=experiment['budget']['request_seconds'],
        fresh_action=True, documentation=load(experiment.get('documentation')),
        model=experiment['model']['name'], **extra)
    service = ObserveNative(cluster_service(root/'native', task=task))
    attempt = NativeJournal(root/'controllers'/str(time.time_ns()))
    from agentcfd_bench.science_campaign import process_identity
    exit_binding = {'launch_id': args.launch_id, 'process_identity': process_identity(os.getpid())}
    attempt.write('start', {'pid':os.getpid(), 'resume':args.resume,
        **exit_binding, 'root':str(root),
        'task':task.binding, 'experiment':experiment, 'protocol_hash':protocol_identity(task=task),
        'harness':factory_.identity, 'qualification':str(Path(args.qualification).resolve())})
    emit('controller_started', pid=os.getpid(), task=task.identity,
         model=experiment['model']['name'], root=str(root))
    stop = threading.Event()
    monitor = threading.Thread(target=watch, args=(root, stop), daemon=True)
    monitor.start()
    try:
        result = run(experiment, root, factory_, service, mode='paid')
    except BaseException as exc:
        from agentcfd_bench.diagnostics import exception_record
        details = exception_record(exc, secrets=(key,))
        attempt.write('exit', {**exit_binding, **details, 'exit_code':1})
        emit('controller_failed', **details)
        return 1
    finally:
        stop.set()
        monitor.join(timeout=5)
    attempt.write('exit', {**exit_binding, 'exit_code':0 if result['lifecycle']=='completed' else 2,
                           'result':result})
    emit('controller_finished', **result)
    return 0 if result['lifecycle']=='completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
