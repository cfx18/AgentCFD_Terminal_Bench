"""Explicit, journalled continuation of a KNOWN truncated Codex response only.

Never redispatch an unknown request, replay a tool, change the model or budgets,
or overwrite old records. The next request is a new continuation in the same
client session. This host recovery does not modify the frozen task/scorer code.
"""
import argparse
import fcntl
import json
from pathlib import Path
import sqlite3
import time

from agentcfd_bench.identity import fingerprint
from agentcfd_bench.journal import NativeJournal,read_receipt
from agentcfd_bench.provider_outcome import inspect_failure,validate_receipt
from agentcfd_bench.adapters.capture import capture_inputs


def recovery_state(root,state,experiment):
    if (state.get('lifecycle')!='interrupted' or state.get('phase')!='blocked'
            or state.get('reason')!='provider_output_truncated'
            or state.get('harness_identity',{}).get('name')!='codex'):
        raise ValueError('Only a known truncated Codex response may be continued')
    if state.get('known_truncation_recoveries',0)>=2:
        raise ValueError('Two recorded continuations exhausted; require a provider fix')
    if state['calls']>=experiment['budget']['model_calls']:
        raise ValueError('No remaining model calls; cannot reset the budget')
    root=Path(root); current=root/'turns'/f"{state['turns']:06d}"
    failed=validate_receipt(read_receipt(current/'error.json'))
    if (failed is None or failed['failure']!=state.get('model_failure')
            or failed['failure']['provider_outcome']!='known'):
        raise ValueError('No intact known provider failure receipt')
    # The last client submission must independently reproduce that failure.
    candidates=[]
    old_request=read_receipt(current/'request.json')
    for path in (root/'agent').glob('*/submission-*'):
        result=read_receipt(path/'client_result.json')
        exit=read_receipt(path/'exit.json')
        prompt=read_receipt(path/'prompt.json')
        if (not result or not exit or exit.get('interrupted') or exit.get('timed_out')
                or result.get('completed') is not False or not prompt
                or prompt.get('remaining_calls')!=old_request['remaining_calls']): continue
        if inspect_failure(path/'api')==failed['failure']:
            candidates.append((path,result,exit))
    if len(candidates)!=1: raise ValueError('Ambiguous or absent failed client session')
    path,client,exit=candidates[0]
    launch=read_receipt(path/'launch.json')
    if launch.get('identity')!=state['harness_identity'] or not client.get('session'):
        raise ValueError('Client identity/session mismatch')
    # All provider requests are terminal and all client processes have exited.
    if exit.get('model_calls')!=failed['model_calls']:
        raise ValueError('Failure call accounting mismatch')
    if old_request['remaining_calls']!=experiment['budget']['model_calls']-state['calls']+failed['model_calls']:
        raise ValueError('Global remaining-call accounting mismatch')
    captured=capture_inputs(path.parent/'work')
    if captured['invalid']: raise ValueError('Cannot recover an unsafe workspace')
    events=[json.loads(line) for line in (path/'events.jsonl').read_text().splitlines() if line.strip()]
    if not any(e.get('type')=='turn.failed' for e in events): raise ValueError('Client terminal failure missing')
    recovered=dict(state)
    recovered['history']=[*state['history'],{'role':'assistant','content':json.dumps({'events':events}),
        'harness_session':{'identity':state['harness_identity'],'workspace':path.parent.name,
                          'session':client['session'],'index':int(path.name.split('-')[-1])}},
        {'role':'user','content':json.dumps({'status':'provider_response_truncated',
            'message':'The previous provider request returned finish_reason=length without a usable response. '
                      'Its token usage and call are recorded. No tool from that incomplete response was executed. '
                      'Continue the same task from the existing files and conversation. '
                      'No new physical acceptance feedback is available.'})}]
    recovered.update(files=captured['files'],lifecycle='interrupted',verdict='not_evaluated',phase='agent',
                     reason='known_provider_truncation_continuation_ready',
                     known_truncation_recoveries=state.get('known_truncation_recoveries',0)+1)
    # Counters and the original failure remain intact and visible in reporting.
    for key in ('calls','usage','model_seconds','native_seconds','turns','runs','protocol_hash','task_digest'):
        if recovered[key]!=state[key]: raise ValueError('Recovery changed measured accounting or protocol')
    return recovered,{'version':'known-truncation-continuation-v1','source_turn':state['turns'],
        'client_submission':str(path),'source_error_hash':fingerprint(failed),
        'state_before_hash':fingerprint(state),'state_after_hash':fingerprint(recovered),
        'calls_preserved':state['calls'],'remaining_calls':experiment['budget']['model_calls']-state['calls'],
        'same_client_session':client['session'],'new_request_not_replay':True}


def prepare(root):
    root=Path(root)
    with (root/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        db=sqlite3.connect(root/'state.sqlite')
        db.execute('PRAGMA synchronous=FULL')
        try:
            db.execute('BEGIN IMMEDIATE')
            state=json.loads(db.execute('SELECT payload FROM state').fetchone()[0])
            experiment=json.loads(db.execute('SELECT payload FROM meta').fetchone()[0])
            recovered,receipt=recovery_state(root,state,experiment)
            journal=NativeJournal(root/'recoveries'/str(time.time_ns()))
            journal.write('prepared',receipt)
            db.execute('UPDATE state SET payload=?',(json.dumps(recovered,sort_keys=True),))
            db.execute('INSERT INTO events(kind,payload) VALUES(?,?)',('known_truncation_continuation',json.dumps(receipt,sort_keys=True)))
            db.commit()
            journal.write('committed',{'state_hash':fingerprint(recovered)})
        finally: db.close()
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True); parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not args.apply: parser.error('Explicit --apply required; does not launch a model')
    print(json.dumps(prepare(args.root),sort_keys=True))
