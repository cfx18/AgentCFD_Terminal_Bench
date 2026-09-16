"""Serial, independently supervised Fable study: qualify each task, then evaluate.

Run this file from a frozen runtime snapshot. Never repeat the completed s-105.
On a task-local error preserve evidence, mark it explicitly, and advance the list.
No unknown provider request is resent. Resumption requires explicit review.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from agentcfd_bench.journal import NativeJournal
from agentcfd_bench.qualification import qualify,protocol_identity
from agentcfd_bench.runtime import cluster_service
from agentcfd_bench.task_package import load_task

from run_codex_science import ObserveNative


def emit(kind,**values):
    print(json.dumps({'time':datetime.now(timezone.utc).isoformat(),'kind':kind,**values},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True); parser.add_argument('--legacy-root',required=True)
    parser.add_argument('--env-file',required=True); parser.add_argument('--root',required=True)
    parser.add_argument('--qualification-root',required=True)
    parser.add_argument('--allow-paid',action='store_true')
    args=parser.parse_args()
    if not args.allow_paid: parser.error('Explicit --allow-paid required')
    project=Path(args.project).resolve(); root=Path(args.root).resolve()
    root.mkdir(parents=True,exist_ok=False)
    journal=NativeJournal(root/'campaign')
    tasks=['s-205','s-203','s-202','s-204']
    journal.write('spec',{'pid':os.getpid(),'tasks':[load_task(t).binding for t in tasks],
        'protocol_hashes':{t:protocol_identity(task=load_task(t)) for t in tasks},
        'model':'AWS-Claude-Fable-5','paid_authorized':True,
        'provider_concurrency':1,'native_concurrency':1,'retained_previous_task':'s-105'})
    emit('campaign_started',pid=os.getpid(),tasks=tasks,root=str(root))
    for task_id in tasks:
        task=load_task(task_id); qualification=Path(args.qualification_root).resolve()/task_id
        emit('qualification_started',task=task_id)
        try:
            originals=project/'runs'/('fable-edge-originals-001' if task_id in ('s-203','s-205') else 'fable-edge-originals-002')/task_id
            result=qualify(qualification,ObserveNative(cluster_service(qualification/'native',task=task)),
                           task=task,positive_source=originals)
            emit('qualification_finished',task=task_id,passed=result['passed'],checks=result['checks'])
            if not result['passed']:
                journal.write(task_id,{'status':'qualification_failed','checks':result['checks'],'model_calls':0})
                continue
            command=[sys.executable,'-u','-B',str(Path(__file__).with_name('run_codex_science.py')),
                '--experiment',str(project/'experiments'/('fable-edge-'+task_id+'-v1.json')),
                '--root',str(root/'trials'/task_id),'--qualification',str(qualification),
                '--env-file',args.env_file,'--legacy-root',args.legacy_root,'--allow-paid']
            emit('paid_trial_started',task=task_id)
            outcome=subprocess.run(command,check=False)
            journal.write(task_id,{'status':'trial_exited','returncode':outcome.returncode,
                                   'trial_root':str(root/'trials'/task_id)})
            emit('paid_trial_exited',task=task_id,returncode=outcome.returncode)
        except Exception as exc:
            journal.write(task_id,{'status':'infrastructure_error','type':type(exc).__name__,
                                   'detail':str(exc)[:2000]})
            emit('task_error',task=task_id,type=type(exc).__name__,detail=str(exc)[:1000])
    rows={task_id:journal.read(task_id) for task_id in tasks}
    journal.write('finished',rows)
    emit('campaign_finished',tasks=rows)


if __name__=='__main__': main()
