"""Offline tests: no real credentials, network, clients, or OpenFOAM."""
import copy
import json

import httpx
import pytest

from probe_model import probe
from agentcfd_bench.journal import read_receipt


def fake_client(responses, seen):
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['trust_env'] is False
            assert kwargs['follow_redirects'] is False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, *, headers, json):
            seen.append(copy.deepcopy(json))
            result = responses.pop(0)
            if isinstance(result, Exception):
                raise result
            return result(json) if callable(result) else result
    return Client


def tool_reply(body):
    marker = body['messages'][0]['content'].split('marker ')[1].split('.')[0]
    return httpx.Response(200, json={'model': body['model'], 'choices': [{
        'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
        'tool_calls': [{'id': 'call-1', 'type': 'function', 'function': {
            'name': 'record_probe', 'arguments': json.dumps({'marker': marker})}}]}}]})


def test_round_trip_does_not_inject_output_cap_or_temperature(tmp_path):
    seen = []
    final = httpx.Response(200, json={'model': 'example', 'choices': [{
        'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'PROBE_OK'}}]})
    result = probe(tmp_path/'probe', endpoint='https://example.invalid', credential='FAKE_SECRET',
                   model='example', client_factory=fake_client([tool_reply, final], seen))
    assert result['passed'] and result['calls'] == 2 and result['benchmark_score'] is False
    assert all(not {'max_tokens', 'max_output_tokens', 'temperature'} & body.keys() for body in seen)
    assert 'content' not in seen[1]['messages'][1]
    assert seen[1]['messages'][2]['tool_call_id'] == 'call-1'
    assert all('FAKE_SECRET' not in p.read_text() for p in (tmp_path/'probe').rglob('*.json'))


@pytest.mark.parametrize('response,outcome', [
    (httpx.Response(503, text='no channel: FAKE_SECRET'), 'upstream_http_error'),
    (httpx.ReadTimeout('unknown'), 'request_outcome_unknown'),
    (httpx.Response(200, json={}), 'malformed_provider_response'),
    (httpx.Response(200, json={'choices': [{'finish_reason': 'content_filter',
                                         'message': {'content': None}}]}), 'upstream_content_filter'),
    (httpx.Response(200, json={'choices': [{'finish_reason': 'length',
                                         'message': {'content': None}}]}), 'upstream_length'),
    (httpx.Response(200, json={'choices': [{'finish_reason': 'stop',
                                         'message': {'content': 'no tool'}}]}), 'tool_call_contract_failed'),
])
def test_error_is_not_retried_or_scored(tmp_path, response, outcome):
    seen = []
    result = probe(tmp_path/'probe', endpoint='https://example.invalid/v1', credential='FAKE_SECRET',
                   model='example', client_factory=fake_client([response], seen))
    assert not result['passed'] and result['outcome'] == outcome and result['calls'] == len(seen) == 1
    assert all('FAKE_SECRET' not in p.read_text() for p in (tmp_path/'probe').rglob('*.json'))
    complete = read_receipt(tmp_path/'probe/call-001/complete.json')
    assert (complete is None) == (outcome == 'request_outcome_unknown')


def test_existing_probe_cannot_be_replayed(tmp_path):
    (tmp_path/'probe').mkdir()
    with pytest.raises(FileExistsError):
        probe(tmp_path/'probe', endpoint='https://example.invalid', credential='fake', model='example')
