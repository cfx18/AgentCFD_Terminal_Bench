"""Explicit single-request Kimi-K3 connectivity probe, not a benchmark score."""
import argparse
import json
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

from agentcfd_bench.journal import NativeJournal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--allow-paid', action='store_true')
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error('One real provider request requires --allow-paid')
    values = dotenv_values(args.env_file)
    endpoint = values.get('SCIENCE_API_BASE') or values.get('OPENAI_BASE_URL')
    credential = values.get('SCIENCE_API_KEY') or values.get('OPENAI_API_KEY')
    if not endpoint or not credential:
        parser.error('Explicit provider URL and key are required')
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=False)
    journal = NativeJournal(root)
    request = {'model': 'Kimi-K3', 'messages': [{'role': 'user', 'content': 'Reply with OK.'}],
               'max_tokens': 1024, 'stream': False}
    journal.write('request', request)
    started = time.monotonic()
    journal.write('dispatch', {'time': time.time(), 'automatic_retries': 0})
    try:
        with httpx.Client(timeout=httpx.Timeout(120, connect=15), trust_env=False) as client:
            response = client.post(endpoint.rstrip('/') + '/chat/completions',
                headers={'Authorization': 'Bearer ' + credential}, json=request)
        # Do not retain headers, credentials, or arbitrary error text from a gateway.
        try:
            data = response.json()
        except ValueError:
            data = {}
        choices = data.get('choices', []) if isinstance(data, dict) else []
        message = choices[0].get('message', {}) if choices else {}
        content = message.get('content')
        record = {'http_status': response.status_code, 'requested_model': 'Kimi-K3',
            'returned_model': data.get('model') if isinstance(data, dict) else None,
            'content_present': isinstance(content, str) and bool(content.strip()),
            'finish_reason': choices[0].get('finish_reason') if choices else None,
            'elapsed_seconds': round(time.monotonic() - started, 3),
            'outcome': 'received_response', 'benchmark_score': False}
        record['passed'] = response.is_success and record['content_present']
    except httpx.HTTPError as exc:
        record = {'outcome': 'request_outcome_unknown', 'error_type': type(exc).__name__,
                  'elapsed_seconds': round(time.monotonic() - started, 3),
                  'passed': False, 'benchmark_score': False}
    journal.write('result', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
