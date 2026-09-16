"""One native AMI equivalence diagnostic; no model calls or reference reruns.

Run from this implementation's project root with --execute-native. The original
completed baseline is read only. A fresh variant adds only the four AMI value
initializers; outputs and receipt identities remain in a separate directory.
Re-entry observes the same operation, never starts a replacement for ambiguity.
This diagnostic is not a replacement for release qualification.
"""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentcfd_bench.identity import fingerprint
from agentcfd_bench.journal import NativeJournal
from agentcfd_bench.qualification import protocol_identity
from agentcfd_bench.runtime import Pending, cluster_service
from agentcfd_bench.task_package import load_task
from agentcfd_bench.tutorial_acceptance import distances
from agentcfd_bench.foam.science_metrics import snapshot


def run(output):
    task = load_task('s-102')
    acceptance = task.acceptance()
    reference = task.reference().reference_files()
    files = dict(reference)
    for name in ('0/U', '0/p'):
        marker = 'type            cyclicAMI;'
        if files[name].count(marker) != 2:
            raise ValueError('Original AMI patch entries changed')
        files[name] = files[name].replace(marker, marker+'\n        value $internalField;')
    changed = sorted(k for k in files if files[k] != reference[k])
    if changed != ['0/U','0/p']:
        raise ValueError('Diagnostic changed more than AMI initializers')
    contract = acceptance.physics_contract(files)
    if contract != {'passed':True,'violations':[]}:
        raise ValueError('Run this diagnostic with the corrected contract implementation')
    journal = NativeJournal(Path(output))
    spec = {'schema':'ami-initial-value-native-control-v1', 'task':task.binding,
            'code_hash':protocol_identity(task=task), 'input_hash':fingerprint(files),
            'original_input_hash':fingerprint(reference), 'changed_inputs':changed,
            'edit':'add value $internalField to AMI1/AMI2 in U and p only',
            'model_calls':0, 'reference_reruns':0}
    if journal.read('spec') is None:
        journal.write('spec',spec)
    if journal.read('spec') != spec:
        raise ValueError('Diagnostic version changed; do not reuse its native receipts')
    saved = journal.read('assessment')
    if saved is not None:
        return saved
    service = cluster_service(journal.root/'native',task=task)
    deadline = time.monotonic()+600
    while True:
        try:
            native = service.execute('r-000001',files,120)
            break
        except Pending:
            if time.monotonic() >= deadline:
                raise  # Unknown native outcomes are not fresh submissions.
            time.sleep(10)
    baseline = json.loads((task.root/'solution/baseline.json').read_text())
    policy = json.loads((task.root/'environment/acceptance-policy.json').read_text())
    if native['verdict'] == 'pass':
        observed = snapshot(native['artifacts'],json.loads((task.root/'solution/profile.json').read_text()))
        measures = observed['measurements']
        evaluation = acceptance.evaluate({'action':'report','run_id':'r-000001','measurements':measures},native)
        errors = distances(observed['fields'],baseline['snapshot']['fields'],policy)
        same_fields = observed['fields'] == baseline['snapshot']['fields']
    else:
        evaluation, errors, same_fields = {'verdict':'not_evaluated'}, {}, False
    result = {**spec, 'native_verdict':native['verdict'],'native_stage':native['stage'],
              'native_reason':native['reason'], 'native_result_hash':fingerprint(native),
              'baseline_hash':fingerprint(baseline),'contract':contract,
              'evaluation':evaluation,'distances':errors,'exact_same_final_fields':same_fields}
    journal.write('assessment',result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--execute-native',action='store_true')
    args = parser.parse_args()
    if not args.execute_native:
        parser.error('Explicit --execute-native required; this acquires one short cluster allocation')
    result = run(args.output)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    raise SystemExit(0 if result['evaluation']['verdict'] == 'pass' else 1)
