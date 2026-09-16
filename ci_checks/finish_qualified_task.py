"""Finish one unchanged, not-yet-started task after explicit prerequisite receipts."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from agentcfd_bench.journal import NativeJournal,read_receipt
from agentcfd_bench.qualification import qualify,protocol_identity
from agentcfd_bench.runtime import cluster_service
from agentcfd_bench.task_package import load_task
from run_codex_science import ObserveNative
from after_test_gate import verdict


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('project','task','root','qualification','original','runtime','env-file','legacy-root','junit','controller-root'):
        parser.add_argument('--'+key,required=True)
    parser.add_argument('--after-receipt',required=True,action='append')
    parser.add_argument('--allow-paid',action='store_true')
    args=parser.parse_args()
    if not args.allow_paid: parser.error('Explicit paid permission required')
    root=Path(args.root); journal=NativeJournal(args.controller_root)
    task=load_task(args.task)
    if root.exists(): raise FileExistsError('Never substitute or rerun an existing trial')
    journal.write('spec',{'task':task.binding,'protocol_hash':protocol_identity(task=task),
        'after_receipts':args.after_receipt,'junit':args.junit,'model':'AWS-Claude-Fable-5'})
    while not all(Path(p).is_file() for p in args.after_receipt) or not Path(args.junit).is_file(): time.sleep(15)
    for path in args.after_receipt: read_receipt(path)
    tests=verdict(args.junit); journal.write('test_gate',tests)
    if not tests['passed']: raise ValueError('Free regression gate did not pass')
    qualification=Path(args.qualification)
    result=qualify(qualification,ObserveNative(cluster_service(qualification/'native',task=task)),
                   task=task,positive_source=args.original)
    print(json.dumps({'kind':'qualification_finished','task':args.task,'passed':result['passed'],'checks':result['checks']}),flush=True)
    if not result['passed']:
        journal.write('finished',{'status':'qualification_failed','checks':result['checks']})
        raise SystemExit(2)
    command=[sys.executable,'-u','-B',str(Path(args.runtime)/'ci_checks/run_codex_science.py'),
        '--experiment',str(Path(args.project)/'experiments'/('fable-edge-'+args.task+'-v1.json')),
        '--root',str(root),'--qualification',str(qualification),'--env-file',args.env_file,
        '--legacy-root',args.legacy_root,'--allow-paid']
    result=subprocess.run(command,check=False)
    # The same bounded known-truncation continuation policy applies here too.
    from agentcfd_bench.reporting import report
    from recover_known_truncation import prepare
    for attempt in range(1,3):
        data=report(root)
        if data['reason']!='provider_output_truncated' or data['lifecycle']=='completed': break
        receipt=prepare(root); journal.write('continuation-'+str(attempt),receipt)
        result=subprocess.run([*command,'--resume'],check=False)
    journal.write('finished',{'status':'trial_exited','returncode':result.returncode})
