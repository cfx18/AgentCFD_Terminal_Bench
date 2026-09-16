"""Explicit author-native qualification; no model/API calls.

Four controls use the existing durable service: valid, missing U, wrong physics,
and a different graded mesh. --native authorizes real cluster computation.
"""
import argparse
import json
from pathlib import Path

from agentcfd_bench.task_package import load_task
from agentcfd_bench.runtime import cluster_service
from agentcfd_bench.qualification import qualify
from agentcfd_bench.journal import read_receipt
from run_codex_science import ObserveNative


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',default='s-001')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    parser.add_argument('--native-cache',type=Path,
                        help='Reuse four completed native controls; refuse missing receipts, never resubmit')
    args=parser.parse_args()
    if not args.native: parser.error('Explicit --native required; this runs author controls, not models')
    task=load_task(args.task,version='free-mesh-v1')
    if args.native_cache:
        for index in range(1,5):
            if read_receipt(args.native_cache/'runs'/f'r-{index:06d}'/'result.json') is None:
                parser.error('Native cache incomplete; no new computation started')
    service=ObserveNative(cluster_service(args.native_cache or args.output/'native',task=task))
    print(json.dumps({'kind':'author_controls_started','task':task.identity,'model_requests_sent':0,
                      'completed_native_cache':str(args.native_cache) if args.native_cache else None}),flush=True)
    result=qualify(args.output/'qualification',service,real=True,task=task)
    print(json.dumps({'kind':'author_controls_finished','passed':result['passed'],
                      'checks':result['checks'],'model_requests_sent':0},ensure_ascii=False),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
