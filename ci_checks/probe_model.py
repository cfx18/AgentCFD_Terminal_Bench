"""Explicit, at-most-two-call Chat tool round-trip probe. Not a model score.

No shell tool is executed, no output-token ceiling is injected, no credentials
are copied to evidence, and an unknown request is never retried.
"""
import argparse
import json
from pathlib import Path
import time
import uuid

import httpx

from agentcfd_bench.journal import NativeJournal


def probe(root, *, endpoint, credential, model, seconds=600, client_factory=httpx.Client):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    journal = NativeJournal(root)
    marker = uuid.uuid4().hex
    tools = [{'type': 'function', 'function': {
        'name': 'record_probe', 'description': 'Record the supplied probe marker.',
        'parameters': {'type': 'object', 'properties': {'marker': {'type': 'string'}},
                       'required': ['marker'], 'additionalProperties': False}}}]
    messages = [{'role': 'user', 'content':
        'Interface test, not a physics task. Call record_probe with marker ' + marker +
        '. After its tool result, reply exactly PROBE_OK. Do not run any other tool.'}]
    result = {'requested_model': model, 'passed': False, 'benchmark_score': False,
              'calls': 0, 'automatic_retries': 0, 'returned_models': []}
    journal.write('spec', {'model': model, 'wire_api': 'chat', 'max_calls': 2,
                          'request_seconds': seconds, 'benchmark_output_token_cap': None,
                          'mode': 'provider-tool-probe-not-model-score'})
    base = endpoint.rstrip('/')
    url = base + ('/chat/completions' if base.endswith('/v1') else '/v1/chat/completions')
    for index in (1, 2):
        call = NativeJournal(root / f'call-{index:03d}')
        body = {'model': model, 'messages': messages, 'tools': tools, 'stream': False}
        call.write('request', body)
        call.write('dispatch', {'time': time.time(), 'automatic_retries': 0})
        result['calls'] += 1
        start = time.monotonic()
        try:
            with client_factory(timeout=httpx.Timeout(seconds, connect=20),
                                trust_env=False, follow_redirects=False) as client:
                response = client.post(url, headers={'Authorization': 'Bearer ' + credential}, json=body)
            call.write('http', {'status_code': response.status_code,
                               'elapsed_seconds': time.monotonic() - start})
            # Headers are deliberately excluded; defensively redact the actual
            # credential if an upstream error were to echo it into its body.
            raw = response.text.replace(credential, '[credential-redacted]')
            call.write('response', {'text': raw})
            call.write('complete', {'known_response': True, 'status_code': response.status_code})
        except httpx.HTTPError as exc:
            call.write('error', {'type': type(exc).__name__, 'outcome': 'request_outcome_unknown'})
            result.update(outcome='request_outcome_unknown', error_type=type(exc).__name__)
            break
        if not response.is_success:
            result.update(outcome='upstream_http_error', http_status=response.status_code)
            break
        try:
            data = json.loads(raw)
            choice = data['choices'][0]
            message = choice['message']
            result['returned_models'].append(data.get('model'))
            call.write('usage', data.get('usage'))
            if choice.get('finish_reason') in ('content_filter', 'length'):
                result.update(outcome='upstream_' + choice['finish_reason'],
                              finish_reason=choice['finish_reason'])
                break
            if index == 1:
                calls = message.get('tool_calls', [])
                if (choice.get('finish_reason') != 'tool_calls' or len(calls) != 1
                        or calls[0]['function']['name'] != 'record_probe'
                        or not isinstance(calls[0].get('id'), str) or not calls[0]['id']
                        or json.loads(calls[0]['function']['arguments']) != {'marker': marker}):
                    result.update(outcome='tool_call_contract_failed')
                    break
                assistant = {'role': 'assistant', 'tool_calls': calls}
                if message.get('content'):
                    assistant['content'] = message['content']
                if message.get('reasoning_content'):
                    assistant['reasoning_content'] = message['reasoning_content']
                messages = [*messages, assistant, {'role': 'tool', 'tool_call_id': calls[0]['id'],
                            'content': json.dumps({'recorded': marker})}]
            else:
                passed = (choice.get('finish_reason') == 'stop'
                          and message.get('content', '').strip() == 'PROBE_OK'
                          and not message.get('tool_calls'))
                result.update(passed=passed, outcome='tool_roundtrip_passed' if passed
                              else 'final_response_contract_failed')
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            result.update(outcome='malformed_provider_response')
            break
    journal.write('result', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--allow-paid', action='store_true')
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error('Real provider probe requires --allow-paid')
    from dotenv import dotenv_values
    values = dotenv_values(args.env_file)
    endpoint = values.get('SCIENCE_API_BASE') or values.get('OPENAI_BASE_URL')
    credential = values.get('SCIENCE_API_KEY') or values.get('OPENAI_API_KEY')
    if not endpoint or not credential:
        parser.error('Explicit provider base URL and API key required')
    result = probe(args.root, endpoint=endpoint, credential=credential, model=args.model)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
