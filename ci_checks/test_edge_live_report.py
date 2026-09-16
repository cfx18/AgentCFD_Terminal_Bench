from agentcfd_bench.journal import NativeJournal
from report_fable_edge import pending_status


def test_no_pending_trial_is_invented(tmp_path):
    old={'status':'qualification_failed'}
    assert pending_status(tmp_path,'s-202',old)==old


def test_deferred_status_keeps_original_failure(tmp_path):
    journal=NativeJournal(tmp_path/'deferred')
    journal.write('spec',{'task':{'id':'s-202'}})
    old={'status':'qualification_failed'}
    result=pending_status(tmp_path,'s-202',old)
    assert result['previous_attempt']==old
    assert result['status']=='修订对照待验收／尚未调用模型'
    assert result['deferred_finished'] is None
    assert pending_status(tmp_path,'s-203',old)==old


def test_deferred_qualification_failure_remains_a_failure(tmp_path):
    journal=NativeJournal(tmp_path/'deferred')
    journal.write('spec',{'task':{'id':'s-202'}})
    journal.write('finished',{'status':'qualification_failed'})
    result=pending_status(tmp_path,'s-202',None)
    assert result['status']=='qualification_failed'
