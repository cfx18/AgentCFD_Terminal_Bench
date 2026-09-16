import io
import json
from types import SimpleNamespace

import httpx
import pytest

from agentcfd_bench.harnesses._transport.adapters import web_research
from agentcfd_bench.records.transcript import Transcript


def exercise(tmp_path, monkeypatch, *, enabled=True, status=200, wrong_model=False, interrupted=False):
    received = []
    real_client = httpx.Client
    def upstream(request):
        received.append(request)
        if interrupted:
            raise httpx.ReadTimeout('fake timeout')
        return httpx.Response(status, json={'output':'reference text', 'results':[]})
    def client(**kwargs):
        assert kwargs['follow_redirects'] is False and kwargs['trust_env'] is False
        return real_client(transport=httpx.MockTransport(upstream))
    monkeypatch.setattr(web_research.httpx, 'Client', client)
    owner = SimpleNamespace(allow_web_search=enabled, model='gpt-6-astra', calls=7,
        endpoint='https://provider.example/backend/responses', directory=tmp_path/'api',
        headers=lambda: {'Authorization':'Bearer HOST-ONLY-TEST'}, seconds=10, network_proxy=None)
    body = {'model':'wrong' if wrong_model else owner.model, 'id':'isolated-session',
            'commands':{'search_query':[{'q':'OpenFOAM buoyancy'}]},
            'settings':{'external_web_access':True}, 'max_output_tokens':10000}
    raw = json.dumps(body).encode()
    class Handler:
        headers = {'Content-Length':str(len(raw)), 'Authorization':'Bearer UNTRUSTED'}
        rfile, wfile = io.BytesIO(raw), io.BytesIO()
        def reject(self, code, message):
            self.status = code
        def send_response(self, code):
            self.status = code
        def send_header(self, *args):
            pass
        def end_headers(self):
            pass
    handler = Handler()
    web_research.WebResearch(owner, Transcript(tmp_path/'trial')).handle(handler)
    assert owner.calls == 7  # Tool searches are not model generations.
    return owner, handler, received, body


@pytest.mark.parametrize('status', [200,429,500])
def test_web_exact_route_evidence_and_error_preservation(tmp_path, monkeypatch, status):
    owner, handler, received, body = exercise(tmp_path, monkeypatch, status=status)
    assert len(received) == 1 and handler.status == status
    assert str(received[0].url) == 'https://provider.example/backend/alpha/search'
    assert received[0].headers['Authorization'] == 'Bearer HOST-ONLY-TEST'
    assert json.loads(received[0].content) == body  # Native search cap not rewritten.
    assert json.loads(handler.wfile.getvalue())['output'] == 'reference text'
    rows=[json.loads(x) for x in (tmp_path/'trial/transcript.jsonl').read_text().splitlines()]
    assert [x['kind'] for x in rows] == ['web_request','web_retrieval']
    assert rows[-1]['payload']['http_status'] == status
    for path in tmp_path.rglob('*'):
        if path.is_file():
            assert b'HOST-ONLY-TEST' not in path.read_bytes()
            assert b'UNTRUSTED' not in path.read_bytes()


@pytest.mark.parametrize('options,code', [({'enabled':False},403),({'wrong_model':True},400)])
def test_web_disabled_or_wrong_model_never_dispatches(tmp_path, monkeypatch, options, code):
    _, handler, received, _ = exercise(tmp_path,monkeypatch,**options)
    assert handler.status == code and received == []


def test_web_unknown_outcome_not_automatically_retried(tmp_path, monkeypatch):
    owner, handler, received, _ = exercise(tmp_path,monkeypatch,interrupted=True)
    assert handler.status == 502 and len(received) == 1
    assert len(list(owner.directory.rglob('interrupted.json'))) == 1
    assert not list(owner.directory.rglob('complete.json'))
