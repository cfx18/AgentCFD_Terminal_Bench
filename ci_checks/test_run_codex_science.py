import pytest

from run_codex_science import ObserveNative, main
from agentcfd_bench.runtime import Pending


@pytest.mark.parametrize('pending', [Pending('unknown_command_outcome'), RuntimeError('123|PENDING|Resources')])
def test_observe_same_operation_only(pending):
    calls, waits = [], []
    class Service:
        task_identity = {'id':'test'}
        def execute(self, *args):
            calls.append(args)
            if len(calls)==1:
                raise pending
            return {'verdict':'pass'}
    service = ObserveNative(Service(), wait=waits.append)
    assert service.execute('r-000001', {'0/U':'data'}, 120)=={'verdict':'pass'}
    assert calls[0]==calls[1]
    assert waits==[15]
    assert service.task_identity=={'id':'test'}


def test_unknown_infrastructure_error_not_retried():
    class Service:
        task_identity = {}
        def execute(self, *args):
            raise RuntimeError('corrupt receipt')
    def no_wait(_):
        pytest.fail('must not retry')
    with pytest.raises(RuntimeError, match='corrupt'):
        ObserveNative(Service(), wait=no_wait).execute('r-000001', {}, 120)


def test_no_implicit_paid_call(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(['--experiment','missing', '--root',str(tmp_path/'run'),
              '--qualification','missing', '--env-file','missing', '--legacy-root','missing'])
    assert exc.value.code==2
    assert not (tmp_path/'run').exists()
