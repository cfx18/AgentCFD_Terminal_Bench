"""Read-only replay of actual submissions through the new durable scoring boundary.

Compare both original frozen decisions and a supplied, already-reviewed contract
correction. No generated submissions, model calls, native work or official rescore.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', required=True)
    parser.add_argument('--review', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    campaign, review, output = (Path(p).resolve() for p in (args.campaign,args.review,args.output))
    if output.exists() or not output.is_relative_to(PROJECT/'runs'):
        raise ValueError('A new project runs directory is required')
    def no_execution(event, args):
        if event in ('socket.connect', 'subprocess.Popen', 'os.system'):
            raise RuntimeError('Report replay cannot run processes or contact services')
    sys.addaudithook(no_execution)
    from agentcfd_bench.evaluation import evaluate_once
    from agentcfd_bench.identity import fingerprint
    from agentcfd_bench.journal import NativeJournal, read_receipt
    from agentcfd_bench.task_package import load_task
    inputs = {}
    def read(path):
        path = Path(path)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        value = read_receipt(path)
        if value is None:
            raise ValueError('Missing required review evidence')
        inputs[str(path)] = before
        return value
    selection = read(campaign/'private/selection.json')
    reviewed_summary = read(review/'summary.json')
    records = []
    output.mkdir()
    journal = NativeJournal(output)
    for task_id in selection['config']['tasks']:
        task = load_task(task_id)
        assert task.binding == selection['tasks'][task_id]
        acceptance = task.acceptance()
        for harness in selection['config']['harnesses']:
            trial = campaign/'trials'/task_id/harness
            for path in sorted((trial/'run/evaluations').glob('*/result.json')):
                turn_id = path.parent.name
                saved = read(path)
                turn = read(trial/'run/turns'/turn_id/'result.json')
                action = acceptance.parse_action(turn['turn']['files'])
                assert action['action'] == 'report'
                native = read(trial/'run/results'/action['run_id']/'run.json')
                native_inputs = read(trial/'native/runs'/action['run_id']/'inputs.json')
                reviewed = read(review/task_id/harness/('report-'+turn_id+'.json'))
                assert reviewed['action_hash'] == fingerprint(action)
                assert reviewed['native_hash'] == fingerprint(native)
                assert reviewed['input_hash'] == fingerprint(native_inputs)
                assert reviewed['original_evaluation'] == saved
                actual = evaluate_once(NativeJournal(output/task_id/harness/turn_id/'original'),
                                       action, native, task, acceptance)
                assert actual == saved, 'Frozen-result semantics changed'
                contract = acceptance.physics_contract(native_inputs)
                assert contract == reviewed['candidate_contract']
                corrected_native = {**native, 'contract':contract}
                corrected = evaluate_once(NativeJournal(output/task_id/harness/turn_id/'reviewed'),
                                          action, corrected_native, task, acceptance)
                assert corrected == reviewed['candidate_evaluation'], 'Previously reviewed semantics changed'
                records.append({'task':task_id,'harness':harness,'turn':turn_id,
                                'original_verdict':actual['verdict'],'reviewed_verdict':corrected['verdict'],
                                'original_exact':True,'reviewed_exact':True})
    assert len(records) == reviewed_summary['real_reports_replayed']
    assert inputs == {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in inputs}
    summary = {'kind':'pipeline_boundary_replay_not_model_score',
               'time':datetime.now(timezone.utc).isoformat(), 'real_reports_replayed':len(records),
               'original_exact':True,'reviewed_exact':True,'records':records,
               'source_receipts_unchanged':True,'source_receipt_hashes':inputs,
               'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'new_paid_requests':0,'new_native_commands':0,'official_records_changed':False}
    journal.write('summary',summary)
    print(json.dumps({k:summary[k] for k in ('real_reports_replayed','original_exact','reviewed_exact',
                                           'source_receipts_unchanged','new_paid_requests','new_native_commands')}))


if __name__ == '__main__':
    main()
