"""Read-only terminal campaign audit; create new review receipts, never resume."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root, candidate, output = [Path(v).resolve() for v in
                               (args.campaign, args.candidate, args.output)]
    if output.exists() or not output.is_relative_to(PROJECT):
        raise ValueError('New project-local audit directory required')
    from agentcfd_bench.journal import NativeJournal, read_receipt
    from agentcfd_bench.science_campaign import check_selection, report, process_identity
    check_selection(root)
    snapshot = report(root)
    assert snapshot['controller']['alive'] is False
    assert snapshot['controller']['exit']['status'] == 'finished'
    assert set(snapshot['lifecycle']) <= {'completed', 'interrupted'}
    spec = importlib.util.spec_from_file_location('agentcfd_bench._candidate_outcome_audit',
                                                 candidate/'agentcfd_bench/provider_outcome.py')
    classifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(classifier)
    records = []
    for row in snapshot['trials']:
        trial = Path(row['evidence'])
        calls, clients = [], []
        for submission in sorted((trial/'agent').glob('*/submission-*')):
            proc, exit_record = [read_receipt(submission/(n+'.json')) for n in ('process', 'exit')]
            assert proc and exit_record is not None
            # Client receipts currently contain only pid, not boot/start identity.
            # A full process_identity dict differs even for a live process.
            # Require absence, conservatively rejecting PID reuse as well.
            assert not (Path('/proc')/str(proc['pid'])).exists(), ('Recorded client PID still present', submission)
            local = []
            for call in sorted((submission/'api').glob('call-*')):
                dispatch = read_receipt(call/'dispatch.json')
                assert dispatch is not None
                known = read_receipt(call/'complete.json')
                error = read_receipt(call/'error.json')
                raw_path = call/'response.raw'
                info = {'path':str(call.relative_to(root)), 'dispatch':dispatch,
                        'complete':known, 'error':error,
                        'evidence_sha256':{p.name:sha(p) for p in call.iterdir() if p.is_file()}}
                for p in call.glob('*.json'):
                    read_receipt(p)
                if known is not None:
                    assert raw_path.is_file()
                    raw = json.loads(raw_path.read_text())
                    assert raw.get('model', '').casefold() == 'kimi-k3'
                    choice = raw['choices'][0]
                    message = choice['message']
                    info['response_summary'] = {
                        'model':raw['model'], 'finish_reason':choice['finish_reason'],
                        'text_characters':len(message.get('content') or ''),
                        'tool_calls':len(message.get('tool_calls') or []),
                        'reasoning_characters':len(message.get('reasoning_content') or '')}
                local.append(info)
            events = [json.loads(line) for line in (submission/'events.jsonl').read_text().splitlines() if line]
            retries = [e for e in events if e.get('type') == 'turn.step.retrying']
            results = [e for e in events if e.get('type') == 'result']
            stderr = (submission/'stderr.log').read_text()
            clients.append({'path':str(submission.relative_to(root)), 'process':proc,
                            'exit':exit_record, 'client_result':read_receipt(submission/'client_result.json'),
                            'recorded_process_not_alive':True,
                            'result_status':[{'subtype':e.get('subtype'), 'is_error':e.get('is_error'),
                                              'result':e.get('result') if e.get('is_error') else None} for e in results],
                            'retry_events':retries, 'declared_retry_seconds':sum(e.get('delay_ms',0) for e in retries)/1000,
                            'broken_pipe_count':stderr.count('BrokenPipeError:'),
                            'connection_reset_count':stderr.count('ConnectionResetError:'),
                            'evidence_sha256':{n:sha(submission/n) for n in
                                               ('exit.json','process.json','events.jsonl','stderr.log','client_result.json')}})
            calls.extend(local)
        assert len(calls) == row['model_calls'] == row['live_requests']['started']
        native = []
        for path in sorted((trial/'native/runs').glob('r-*')):
            assert read_receipt(path/'released.json') == {'released':True}
            result = read_receipt(path/'result.json')
            assert result is not None
            native.append({'path':str(path.relative_to(root)), 'result_sha256':sha(path/'result.json'),
                           'released':True, 'handle':read_receipt(path/'handle.json')})
        failure = None
        if row['verdict'] == 'error':
            last = sorted((trial/'agent').glob('*/submission-*'))[-1]
            failure = classifier.inspect_failure(last/'api', timed_out=clients[-1]['exit']['timed_out'])
        records.append({'task':row['task_id'], 'harness':row['harness'],
                        'original_lifecycle':row['lifecycle'], 'original_verdict':row['verdict'],
                        'original_reason':row.get('reason'), 'review_failure':failure,
                        'calls':calls, 'clients':clients, 'native':native})
    check_selection(root)
    assert report(root) == snapshot
    journal = NativeJournal(output)
    journal.write('campaign-snapshot', snapshot)
    journal.write('audit', {'time':datetime.now(timezone.utc).isoformat(),
                           'kind':'closed_campaign_read_only_audit', 'records':records,
                           'all_registered_trials_terminal':True, 'selection_verified_before_deployment':True,
                           'script_sha256':sha(Path(__file__)), 'classifier_sha256':sha(candidate/'agentcfd_bench/provider_outcome.py'),
                           'new_paid_requests':0, 'new_native_commands':0,
                           'limitations':['Recorded PID identities only, not exhaustive descendant audit.',
                                          'Stored HTTP response does not prove delivery to the client.',
                                          'Candidate failure classification does not overwrite original scores.']})
    print(json.dumps({'output':str(output), 'trials':len(records), 'calls':sum(len(r['calls']) for r in records),
                      'clients':sum(len(r['clients']) for r in records),
                      'known_responses':sum(c['complete'] is not None for r in records for c in r['calls']),
                      'interrupted_reviews':[{k:r[k] for k in ('task','harness','review_failure')}
                                             for r in records if r['review_failure']]}))


if __name__ == '__main__':
    main()
