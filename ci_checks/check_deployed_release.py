"""Test exact deployed candidate bytes with local fake APIs, never paid/native work."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import site
import socket
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_map(project):
    return {str(p.relative_to(project)):sha(p)
            for folder in ('agentcfd_bench','tests','tasks','resources','experiments')
            for p in (project/folder).rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--closure', required=True)
    parser.add_argument('--campaign', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    candidate, closure, campaign, output = [Path(v).resolve() for v in
        (args.candidate, args.closure, args.campaign, args.output)]
    if output.exists() or not output.is_relative_to(PROJECT):
        raise ValueError('New project-local test evidence directory required')
    from agentcfd_bench.journal import NativeJournal, read_receipt
    from agentcfd_bench.science_campaign import report, check_selection
    from agentcfd_bench.qualification import protocol_identity
    from agentcfd_bench.task_package import load_task
    closed = read_receipt(closure/'audit.json')
    assert closed['all_registered_trials_terminal'] and closed['selection_verified_before_deployment']
    current = report(campaign)
    assert set(current['lifecycle']) <= {'completed','interrupted'}
    assert not current['controller']['alive'] and current['controller']['exit']['status'] == 'finished'
    expected = source_map(candidate)
    before = source_map(PROJECT)
    assert expected == before, 'Final deployed source must exactly match reviewed candidate'
    try:
        check_selection(campaign)
    except ValueError as exc:
        assert 'changed' in str(exc).lower()
    else:
        raise AssertionError('Old paid campaign must reject the new protocol on resume')
    protocols = {name:protocol_identity(task=load_task(name)) for name in
                 read_receipt(campaign/'private/selection.json')['config']['tasks']}
    output.mkdir()
    journal = NativeJournal(output)
    runner_hash = sha(Path(__file__))
    journal.write('spec', {'kind':'final_deployed_source_regression', 'source_files':before,
                          'candidate':str(candidate), 'closure_sha256':sha(closure/'audit.json'),
                          'protocol_hashes':protocols, 'old_run_resume_rejected':True,
                          'runner_sha256':runner_hash, 'runner_source':Path(__file__).read_text()})
    site.addsitedir('/usr/local/lib/python3.12/dist-packages')
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['FOAMCLAW_TEST_CODEX_ISOLATION'] = '1'
    for key in list(os.environ):
        if any(word in key.upper() for word in ('API_KEY','SECRET','ACCESS_TOKEN','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY')):
            del os.environ[key]
    forbidden, launches = [], []
    def audit(event, values):
        if event == 'socket.connect':
            sock, address = values
            if sock.family != socket.AF_UNIX and (not isinstance(address,tuple) or
                    address[0] not in ('127.0.0.1','::1','localhost')):
                forbidden.append({'event':event,'address':str(address)})
                raise RuntimeError('Tests may only connect to local fake APIs')
        if event == 'subprocess.Popen':
            executable, argv, *_ = values
            if Path(executable).name not in ('python','python3','python3.12','bwrap') or any(
                    flag in argv for flag in ('--allow-paid','--execute-native')):
                forbidden.append({'event':event,'executable':str(executable)})
                raise RuntimeError('No paid API, SSH or native launches in regression tests')
            launches.append({'executable':str(executable),
                             'arguments_hash':hashlib.sha256(json.dumps(argv,default=str).encode()).hexdigest()})
    sys.addaudithook(audit)
    os.chdir(PROJECT)
    import pytest
    class Outcomes:
        def __init__(self):
            self.nodes, self.reports = [], []
        def pytest_collection_modifyitems(self, items):
            self.nodes = [i.nodeid for i in items]
        def pytest_runtest_logreport(self, report):
            self.reports.append({'node':report.nodeid,'phase':report.when,'outcome':report.outcome})
    outcomes = Outcomes()
    cases = Path(tempfile.mkdtemp(prefix='ab-release-'))/'cases'
    code = pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(cases),
                        '--junitxml',str(output/'junit.xml'),'tests'], plugins=[outcomes])
    after = source_map(PROJECT)
    data = {'kind':'final_deployed_source_regression', 'time':datetime.now(timezone.utc).isoformat(),
            'collected':len(outcomes.nodes), 'tests':outcomes.nodes, 'reports':outcomes.reports,
            'passed':sum(r['phase']=='call' and r['outcome']=='passed' for r in outcomes.reports),
            'failed_reports':sum(r['outcome']=='failed' for r in outcomes.reports),
            'skipped_reports':sum(r['outcome']=='skipped' for r in outcomes.reports),
            'pytest_exit':int(code), 'python':sys.version, 'pytest':pytest.__version__,
            'source_files_unchanged':before==after, 'candidate_matches':after==source_map(candidate),
            'runner_unchanged':sha(Path(__file__))==runner_hash, 'runner_sha256':runner_hash,
            'forbidden_attempts':forbidden, 'process_launches':launches, 'test_case_root':str(cases),
            'actual_client_tests_enabled':True, 'old_run_resume_rejected':True,
            'protocol_hashes':protocols, 'new_paid_requests':0, 'new_native_commands':0,
            'scope':'Local fake APIs, real installed clients; not native qualification or model scores.'}
    journal.write('summary', data)
    print(json.dumps({k:data[k] for k in ('collected','passed','failed_reports','skipped_reports',
                                        'pytest_exit','source_files_unchanged','candidate_matches','forbidden_attempts')}))
    return int(code) or int(bool(forbidden) or before!=after or not data['candidate_matches']
                           or not data['runner_unchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
