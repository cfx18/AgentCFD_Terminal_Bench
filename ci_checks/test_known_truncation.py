import copy
import json

import pytest

from agentcfd_bench.journal import NativeJournal,read_receipt
from agentcfd_bench.provider_outcome import details
from recover_known_truncation import recovery_state
from after_test_gate import verdict


@pytest.fixture
def failed(tmp_path):
    root=tmp_path; identity={'name':'codex','model':'AWS-Claude-Fable-5'}
    failure=details('known','provider_output_truncated',1,1)
    error={'version':'provider-failure-v1','type':'Error','model_calls':1,'usage':{},'seconds':1,'failure':failure}
    journal=NativeJournal(root/'turns/000001')
    journal.write('error',error); journal.write('request',{'remaining_calls':64})
    path=root/'agent'/('a'*32)/'submission-01'; client=NativeJournal(path)
    client.write('prompt',{'remaining_calls':64})
    client.write('client_result',{'completed':False,'session':'session-known'})
    client.write('exit',{'code':1,'timed_out':False,'model_calls':1})
    client.write('launch',{'identity':identity})
    (path/'events.jsonl').write_text(json.dumps({'type':'turn.failed','error':{'message':'provider failure'}})+'\n')
    (path.parent/'work').mkdir()
    api=NativeJournal(path/'api/call-001')
    api.write('complete',{'status':200})
    (api.root/'response.raw').write_text(json.dumps({'choices':[{'finish_reason':'length','message':{'content':None}}]}))
    state={'lifecycle':'interrupted','phase':'blocked','verdict':'error','reason':'provider_output_truncated',
       'harness_identity':identity,'model_failure':failure,'calls':1,'turns':1,'usage':{},'model_seconds':1,
       'native_seconds':0,'runs':0,'protocol_hash':'unchanged','task_digest':'unchanged',
       'history':[],'files':{}}
    return root,state,{'budget':{'model_calls':64}},path


def test_known_continuation_preserves_accounting_and_session(failed):
    root,state,exp,path=failed; old=copy.deepcopy(state)
    new,receipt=recovery_state(root,state,exp)
    assert state==old and new['calls']==1 and receipt['remaining_calls']==63
    assert new['history'][-2]['harness_session']['session']=='session-known'
    assert new['phase']=='agent' and new['known_truncation_recoveries']==1
    assert new['model_failure']==old['model_failure']
    assert read_receipt(root/'turns/000001/error.json')['failure']==state['model_failure']


@pytest.mark.parametrize('problem',['unknown','http','budget','identity','timeout','missing_receipt','repeat'])
def test_no_blind_redispatch(failed,problem):
    root,state,exp,path=failed
    if problem=='unknown': state['model_failure']['provider_outcome']='unknown'
    if problem=='http': state['reason']='provider_http_error'
    if problem=='budget': state['calls']=64
    if problem=='identity': state['harness_identity']={'name':'codex','model':'another'}
    if problem=='timeout': state['reason']='harness_execution_timeout'
    if problem=='missing_receipt': (path/'api/call-001/complete.json').unlink()
    if problem=='repeat': state['known_truncation_recoveries']=2
    with pytest.raises(ValueError): recovery_state(root,state,exp)


@pytest.mark.parametrize('tests,failures,errors,skipped,ok',[(1,0,0,0,True),(0,0,0,0,False),
    (1,1,0,0,False),(1,0,1,0,False),(1,0,0,1,False)])
def test_test_gate_requires_nonempty_fully_passing_report(tmp_path,tests,failures,errors,skipped,ok):
    path=tmp_path/'report.xml'
    outcome = '<failure/>' if failures else '<error/>' if errors else '<skipped/>' if skipped else ''
    case = f'<testcase name="unrelated">{outcome}</testcase>' if tests else ''
    path.write_text(f'<testsuites><testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}">{case}</testsuite></testsuites>')
    assert verdict(path)['passed'] is False  # Even green unbound XML cannot launch.
    from release_evidence import summary
    observed = summary(path)
    assert (observed['green'] and not observed['skipped']) is ok
