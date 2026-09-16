"""Classify durable provider failures without granting permission to redispatch."""
import json
from pathlib import Path

from .journal import read_receipt
from .telemetry import terminal_body

VERSION = 'provider-failure-v1'
REASONS = {
    'model_request_outcome_unresolved', 'model_response_evidence_incomplete',
    'provider_output_truncated', 'provider_content_filtered',
    'provider_response_invalid', 'provider_empty_response',
    'provider_http_error', 'provider_response_failed', 'provider_delivery_failed',
    'provider_model_identity_error',
    'provider_client_retry_rejected',
    'harness_execution_failed', 'harness_execution_timeout',
    'harness_request_not_dispatched',
}


def details(outcome, reason, requests=0, known=0):
    return {'version': VERSION, 'provider_outcome': outcome, 'reason': reason,
            'observed_requests': requests, 'known_responses': known,
            'automatic_retry': False}


def validate_details(value):
    """Only bounded, public status metadata may enter reports; no error prose."""
    if not isinstance(value, dict) or set(value) != {
            'version', 'provider_outcome', 'reason', 'observed_requests',
            'known_responses', 'automatic_retry'}:
        raise ValueError('Invalid provider failure metadata')
    if value['version'] != VERSION or value['automatic_retry'] is not False:
        raise ValueError('Invalid provider failure policy')
    if value['provider_outcome'] not in ('known', 'unknown', 'not_dispatched') or value['reason'] not in REASONS:
        raise ValueError('Invalid provider failure category')
    total, known = value['observed_requests'], value['known_responses']
    if type(total) is not int or type(known) is not int or not 0 <= known <= total:
        raise ValueError('Invalid provider failure accounting')
    if value['provider_outcome'] == 'known' and not (total > 0 and total == known):
        raise ValueError('Known outcome lacks complete receipts')
    if value['provider_outcome'] == 'not_dispatched' and total:
        raise ValueError('Undispatched outcome has requests')
    return dict(value)


def response_problem(body):
    """Inspect terminal status BEFORE accepting text or tool-call payloads."""
    if not isinstance(body, dict):
        return 'provider_response_invalid'
    if body.get('object') == 'response':
        status = body.get('status')
        if status == 'incomplete':
            supplied = body.get('incomplete_details') or {}
            if not isinstance(supplied, dict):
                return 'provider_response_invalid'
            reason = supplied.get('reason')
            return ('provider_output_truncated' if reason in ('length', 'max_output_tokens')
                    else 'provider_content_filtered' if reason == 'content_filter'
                    else 'provider_response_failed')
        if status == 'failed' or body.get('error'):
            return 'provider_response_failed'
        if status != 'completed' or not isinstance(body.get('output'), list):
            return 'provider_response_invalid'
        for item in body['output']:
            if not isinstance(item, dict):
                return 'provider_response_invalid'
            if item.get('type') in ('function_call', 'custom_tool_call'):
                return None
            if item.get('type') == 'message':
                content = item.get('content')
                if isinstance(content, str) and content.strip():
                    return None
                if isinstance(content, list) and any(isinstance(v, dict) and
                        (v.get('text') or v.get('refusal')) for v in content):
                    return None
        return 'provider_empty_response'
    choices = body.get('choices')
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        return 'provider_response_invalid'
    choice = choices[0]
    reason = choice.get('finish_reason')
    if reason == 'length':
        return 'provider_output_truncated'
    if reason == 'content_filter':
        return 'provider_content_filtered'
    if reason not in ('stop', 'tool_calls'):
        return 'provider_response_failed'
    message = choice.get('message')
    if not isinstance(message, dict):
        return 'provider_response_invalid'
    calls = message.get('tool_calls') or []
    content = message.get('content') or ''
    if not isinstance(calls, list) or not isinstance(content, str):
        return 'provider_response_invalid'
    return None if content.strip() or calls else 'provider_empty_response'


class ProviderResponseError(ValueError):
    def __init__(self, reason, finish_reason=None):
        if reason not in REASONS:
            raise ValueError('Unregistered provider response problem')
        super().__init__(reason)
        self.provider_failure = reason
        self.finish_reason = finish_reason if isinstance(finish_reason, str) else None


def inspect_failure(directory, *, timed_out=False):
    """Read-only and conservative: a single unfinished request keeps uncertainty."""
    paths = sorted(Path(directory).glob('call-*'))
    known = 0
    problems = []
    try:
        for path in paths:
            complete = read_receipt(path/'complete.json')
            if complete is None:
                continue
            known += 1
            status = complete.get('status')
            if type(status) is not int:
                problems.append('model_response_evidence_incomplete')
                continue
            if status != 200:
                problems.append('provider_http_error')
                continue
            if complete.get('model_identity_verified') is False:
                problems.append('provider_model_identity_error')
                continue
            raw_path = path/'response.raw'
            if not raw_path.is_file():
                problems.append('model_response_evidence_incomplete')
                continue
            body = terminal_body(raw_path.read_text())
            problem = response_problem(body)
            if problem:
                problems.append(problem)
            elif (path/'delivery_error.json').exists():
                read_receipt(path/'delivery_error.json')
                problems.append('provider_delivery_failed')
        if len(paths) != known:
            return details('unknown', 'model_request_outcome_unresolved', len(paths), known)
        if not paths:
            return details('not_dispatched', 'harness_execution_timeout' if timed_out
                           else 'harness_request_not_dispatched')
        if not problems and (Path(directory)/'retry_rejections').exists():
            problems.append('provider_client_retry_rejected')
        reason = problems[-1] if problems else (
            'harness_execution_timeout' if timed_out else 'harness_execution_failed')
        return details('known', reason, len(paths), known)
    except (ValueError, TypeError, OSError):
        return details('unknown', 'model_response_evidence_incomplete', len(paths), known)


def exception_details(exc):
    value = getattr(exc, 'failure_details', None)
    if value is None:
        return details('unknown', 'model_request_outcome_unresolved')
    try:
        return validate_details(value)
    except ValueError:
        return details('unknown', 'model_response_evidence_incomplete')


def failure_receipt(exc, seconds):
    """Durable accounting and classification, before the state transaction."""
    calls = getattr(exc, 'model_calls', 0)
    if type(calls) is not int or calls < 0:
        calls = 0
    return {'version': VERSION, 'type': type(exc).__name__, 'model_calls': calls,
            'usage': getattr(exc, 'model_usage', None), 'seconds': seconds,
            'failure': exception_details(exc)}


def validate_receipt(value):
    import math
    if not isinstance(value, dict) or value.get('version') != VERSION:
        return None  # Older incomplete records remain unresolved; do not invent accounting.
    if set(value) != {'version', 'type', 'model_calls', 'usage', 'seconds', 'failure'}:
        raise ValueError('Incomplete failed-request receipt')
    if value['usage'] is not None and not isinstance(value['usage'], dict):
        raise ValueError('Invalid failed-request usage')
    if type(value.get('model_calls')) is not int or value['model_calls'] < 0:
        raise ValueError('Invalid failed-request accounting')
    elapsed = value.get('seconds')
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError('Invalid failed-request duration')
    failure = validate_details(value.get('failure'))
    if failure['observed_requests'] > value['model_calls']:
        raise ValueError('Failed-request accounting is incomplete')
    return {**value, 'failure': failure}
