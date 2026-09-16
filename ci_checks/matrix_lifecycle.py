"""Receipt-only matrix recovery and failure circuit; never dispatch work here."""
from pathlib import Path

from agentcfd_bench.journal import read_receipt
from agentcfd_bench.science_campaign import process_identity


class RecoveryBlocked(RuntimeError):
    """An earlier launch cannot safely be classified or repeated."""


def recover_exit(journal, entry, trial, *, identity=process_identity, wait):
    try:
        return _recover_exit(journal, entry, trial, identity=identity, wait=wait)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise RecoveryBlocked('invalid_recovery_evidence:'+type(exc).__name__) from exc


def _recover_exit(journal, entry, trial, *, identity, wait):
    """Observe the original child, then reclaim its launch-bound exit receipt.

    Older launches without this binding remain blocked, not retroactively signed.
    PID alone is not identity: boot ID and /proc start ticks must also match.
    """
    task = entry['task']
    saved = journal.read(task+'-exit')
    if saved is not None:
        return saved
    launch = journal.read(task+'-launch')
    if not launch or not launch.get('launch_id'):
        raise RecoveryBlocked('launch_binding_missing')
    expected = {'launch_id': launch['launch_id'], 'root': str(Path(trial).resolve()),
                'task': entry['task_binding'], 'experiment': entry['experiment'],
                'protocol_hash': entry['protocol_hash']}
    while True:
        matches = []
        for path in sorted((Path(trial)/'controllers').glob('*/start.json')):
            start = read_receipt(path)
            if start.get('launch_id') != expected['launch_id']:
                continue
            if any(start.get(k) != v for k,v in expected.items()) or not start.get('process_identity'):
                raise RecoveryBlocked('controller_binding_mismatch')
            matches.append((path, start))
        if len(matches) > 1:
            raise RecoveryBlocked('multiple_controllers_for_one_launch')
        recorded = journal.read(task+'-process')
        recorded_identity = (recorded or {}).get('identity')
        child_identity = matches[0][1]['process_identity'] if matches else None
        if recorded_identity and child_identity and recorded_identity != child_identity:
            raise RecoveryBlocked('controller_process_identity_mismatch')
        original = recorded_identity or child_identity
        if not original:
            raise RecoveryBlocked('process_start_outcome_unknown')
        if identity(original['pid']) == original:
            wait(5)  # Existing process only; no replacement qualification or model call.
            saved = journal.read(task+'-exit')
            if saved is not None:
                return saved
            continue
        if not matches:
            raise RecoveryBlocked('original_process_gone_without_controller_evidence')
        path, _ = matches[0]
        receipt = read_receipt(path.with_name('exit.json'))
        if receipt is None:
            raise RecoveryBlocked('original_process_gone_without_exit_evidence')
        if (receipt.get('launch_id') != expected['launch_id']
                or receipt.get('process_identity') != original
                or type(receipt.get('exit_code')) is not int):
            raise RecoveryBlocked('controller_exit_binding_mismatch')
        result = {'returncode': receipt['exit_code'], 'recovered_from': str(path.with_name('exit.json')),
                  'launch_id': expected['launch_id'], 'process_identity': original}
        journal.write(task+'-exit', result)
        return result


def infrastructure_failure(row):
    return (row.get('status') == 'infrastructure_error' or row.get('verdict') == 'error'
            or (row.get('status') == 'trial_exited' and row.get('returncode', 0) != 0))


def circuit_reason(rows):
    """Genuine model fail != infrastructure error; absent quota data stays unknown."""
    if not rows or not infrastructure_failure(rows[-1]):
        return None
    if rows[-1].get('reason') in ('model_request_outcome_unresolved', 'provider_delivery_failed',
                                  'provider_client_retry_rejected'):
        return {'policy': 'serial-failure-circuit-v2', 'reason': rows[-1]['reason'],
                'consecutive_limit': 1, 'quota_reset': 'unknown'}
    statuses = rows[-1].get('provider_http_statuses', [])
    for status in (401, 402, 403, 429):
        if status in statuses:
            return {'policy': 'serial-failure-circuit-v1', 'reason': 'provider_http_'+str(status),
                    'quota_reset': 'unknown'}
    if len(rows) >= 2 and infrastructure_failure(rows[-2]):
        return {'policy': 'serial-failure-circuit-v1', 'reason': 'consecutive_infrastructure_errors',
                'consecutive_limit': 2, 'quota_reset': 'unknown'}
    return None


def provider_statuses(trial):
    values = set()
    for path in (Path(trial)/'agent').glob('*/submission-*/api/call-*/complete.json'):
        receipt = read_receipt(path)
        status = receipt.get('http_status', receipt.get('status'))
        if type(status) is int:
            values.add(status)
    return sorted(values)


def check_circuit(journal, entries, *, acknowledge=False):
    """Recompute before advancing, including after a crash before circuit write."""
    rows = []
    for entry in entries:
        row = journal.read(entry['task'])
        if row is None:
            break
        rows.append(row)
        reason = circuit_reason(rows)
        if reason is None:
            continue
        name = 'circuit-'+entry['task']
        saved = journal.read(name)
        if saved is None:
            saved = {**reason, 'after_task': entry['task'], 'state': 'paused'}
            journal.write(name, saved)
        if journal.read(name+'-acknowledged') is not None:
            continue
        if acknowledge:
            journal.write(name+'-acknowledged', {'action': 'explicit_resume_acknowledgement',
                'circuit': saved, 'rerun_previous_trial': False})
            continue
        return saved
    return None
