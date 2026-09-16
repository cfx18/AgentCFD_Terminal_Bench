"""Bind test outcomes to the runtime and an explicit mandatory regression set.

Receipts are created by the pytest plugin DURING testing, not by signing an
arbitrary pre-existing green XML. These are local audit records, not signatures
against a malicious host administrator.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

VERSION = 'source-bound-tests-v1'
REQUIRED_GROUPS = {'test_custom_request_deadline': {
    'test_custom_request_deadline_stops_drip_without_retry',
}, 'test_transport_incident': {
    'test_relay_configured_socket_timeout_is_effective',
    'test_provider_terminal_is_saved_even_if_downstream_disconnects',
    'test_native_terminal_does_not_wait_for_tcp_eof',
    'test_memory_only_relay_header_forwarding',
    'test_memory_only_reported_model_mismatch_rejected',
    'test_test_gate_requires_binding_to_tested_source',
    'test_remote_protocol_error_preserves_partial_bytes_and_closed_evidence',
}, 'test_native_recovery': {
    'test_large_log_read_retries_only_read_not_solver',
    'test_solver_exit_then_log_failure_engine_resume_no_reexecution',
    'test_pending_observation_is_bounded_without_replacement',
}, 'test_provider_recovery': {
    'test_unknown_stays_blocked_until_explicit_acknowledgement',
    'test_recovery_transaction_gap_is_idempotent',
}, 'test_live_transcript': {
    'test_pipe_is_live_while_child_waits_and_preserves_all_raw_bytes',
    'test_engine_records_feedback_and_judgement_without_replay',
}, 'test_subscription_backend': {
    'test_xhigh_explicitly_disables_subagents',
    'test_real_xhigh_client_tools_docs_isolation_and_resume',
    'test_real_xhigh_interrupted_stream_preserves_session_and_explicit_continuation',
}, 'test_matrix_lifecycle': {
    'test_reclaims_bound_child_exit_without_relaunch',
    'test_missing_or_unbound_exit_never_invents_success',
    'test_crash_before_circuit_write_is_recovered_and_requires_explicit_ack',
    'test_matrix_resume_does_not_qualify_or_spawn_again',
}}
REQUIRED = {(module, name) for module, names in REQUIRED_GROUPS.items() for name in names}


def sources(root):
    root = Path(root)
    result = {}
    for folder in ('agentcfd_bench', 'ci_checks', 'tests', 'tasks', 'resources', 'task-drafts'):
        for path in sorted((root/folder).rglob('*')):
            if any(p in ('__pycache__', '.pytest_cache') for p in path.parts) or path.suffix == '.pyc':
                continue
            if path.is_symlink():
                raise ValueError('Symlink in tested sources')
            if path.is_file():
                result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not result:
        raise ValueError('No tested runtime sources')
    return result


def summary(path):
    raw = Path(path).read_bytes()
    root = ET.fromstring(raw)
    cases = list(root.iter('testcase'))
    suites = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
    totals = {k: sum(int(s.get(k, '0')) for s in suites) for k in ('tests','failures','errors','skipped')}
    # Suite counters alone can claim thousands of tests without any testcases.
    if not suites or totals['tests'] != len(cases):
        raise ValueError('JUnit counters differ from actual testcase evidence')
    rows = []
    for case in cases:
        status = ('error' if case.find('error') is not None else 'fail' if case.find('failure') is not None
                  else 'skipped' if case.find('skipped') is not None else 'pass')
        rows.append({'class': case.get('classname',''), 'name': case.get('name',''), 'status': status})
    if len({(r['class'],r['name']) for r in rows}) != len(rows):
        raise ValueError('Duplicate testcase evidence')
    for label, state in (('failures','fail'),('errors','error'),('skipped','skipped')):
        if totals[label] != sum(r['status']==state for r in rows):
            raise ValueError('JUnit outcome counters differ from testcase evidence')
    return {'green': bool(cases) and not totals['failures'] and not totals['errors'],
            **totals, 'cases': rows, 'sha256': hashlib.sha256(raw).hexdigest()}


def sidecar(path):
    return Path(str(path)+'.binding.json')


def check(path, runtime):
    result = summary(path)
    binding = json.loads(sidecar(path).read_text())
    if (binding.get('version') != VERSION or binding.get('junit_sha256') != result['sha256']
            or binding.get('sources_before') != binding.get('sources_after')
            or binding.get('sources_after') != sources(runtime)
            or binding.get('cases') != result['cases'] or binding.get('exit_code') != 0):
        raise ValueError('Test report is unbound, stale, edited or not a successful test execution')
    return {**result, 'bound': True}


def verify(paths, runtime, *, subscription_xhigh=False):
    shards = [check(path, runtime) for path in paths]
    passed = {(r['class'].split('.')[-1], r['name'].split('[',1)[0])
              for s in shards for r in s['cases'] if r['status']=='pass'}
    groups = {k:v for k,v in REQUIRED_GROUPS.items() if subscription_xhigh or k != 'test_subscription_backend'}
    required = {(module,name) for module,names in groups.items() for name in names}
    missing = sorted('::'.join(v) for v in required-passed)
    missing += ['source:tests/'+module+'.py' for module in groups
                if not (Path(runtime)/'tests'/f'{module}.py').is_file()]
    return {'passed': bool(shards) and all(s['green'] for s in shards) and not missing,
            'profile': 'core-and-subscription-xhigh' if subscription_xhigh else 'core',
            'missing_required': missing, 'shards': shards,
            **{k: sum(s[k] for s in shards) for k in ('tests','failures','errors','skipped')}}
