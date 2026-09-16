"""Wait for the serial campaign, then continue known truncated sessions, serially."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from agentcfd_bench.journal import NativeJournal
from agentcfd_bench.reporting import report
from recover_known_truncation import prepare


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True); parser.add_argument('--campaign',required=True)
    parser.add_argument('--qualification-root',required=True); parser.add_argument('--runtime',required=True)
    parser.add_argument('--legacy-root',required=True); parser.add_argument('--env-file',required=True)
    parser.add_argument('--allow-paid',action='store_true')
    args=parser.parse_args()
    if not args.allow_paid: parser.error('Explicit paid continuation permission required')
    project=Path(args.project).resolve(); campaign=Path(args.campaign).resolve()
    journal=NativeJournal(campaign/'continuations')
    journal.write('spec',{'version':'known-truncation-continuation-v1','tasks':['s-203','s-202','s-204'],
        'provider_concurrency':1,'maximum_continuations_per_task':2,
        'global_budget_reset':False,'requires_original_campaign_terminal':True})
    while not (campaign/'campaign/finished.json').is_file(): time.sleep(15)
    for task_id in ('s-203','s-202','s-204'):
        root=campaign/'trials'/task_id
        if not (root/'state.sqlite').is_file(): continue
        for attempt in range(1,3):
            data=report(root)
            if data['lifecycle']=='completed' or data.get('reason')!='provider_output_truncated': break
            try:
                receipt=prepare(root)
            except (ValueError,OSError) as exc:
                journal.write(task_id+'-blocked',{'type':type(exc).__name__,'detail':str(exc)[:1000]})
                break
            print(json.dumps({'kind':'known_continuation_started','task':task_id,'attempt':attempt,**receipt}),flush=True)
            command=[sys.executable,'-u','-B',str(Path(args.runtime)/'ci_checks/run_codex_science.py'),
                '--experiment',str(project/'experiments'/('fable-edge-'+task_id+'-v1.json')),
                '--root',str(root),'--qualification',str(Path(args.qualification_root)/task_id),
                '--env-file',args.env_file,'--legacy-root',args.legacy_root,'--allow-paid','--resume']
            outcome=subprocess.run(command,check=False)
            journal.write(task_id+'-'+str(attempt),{'returncode':outcome.returncode,'receipt':receipt})
    journal.write('finished',{'tasks':{t:report(campaign/'trials'/t)['verdict']
        for t in ('s-203','s-202','s-204') if (campaign/'trials'/t/'state.sqlite').is_file()}})
    print(json.dumps({'kind':'known_continuations_finished'}),flush=True)
