"""Fixed-route Codex standalone search relay; no shell internet or credential forwarding.

Searches are tool operations, recorded separately from the model-generation budget.
No automatic retry, redirects, alternate providers or fabricated search output.
"""
import json
import os
import threading
import time
import uuid

import httpx

from ..journal import NativeJournal
from .codex_bridge import REQUEST_HEADERS, RESPONSE_HEADERS


class WebResearch:
    def __init__(self, broker, transcript):
        self.broker, self.transcript = broker, transcript
        self.lock = threading.Lock()

    def handle(self, handler):
        owner = self.broker
        if not owner.allow_web_search:
            return handler.reject(403, 'Web research is disabled for this experiment')
        try:
            size = int(handler.headers.get('Content-Length', '0'))
            if not 0 < size <= 16 * 1024 * 1024:
                return handler.reject(413, 'Invalid search request size')
            raw = handler.rfile.read(size)
            body = json.loads(raw)
            if (len(raw) != size or not isinstance(body, dict)
                    or body.get('model') != owner.model
                    or not isinstance(body.get('id'), str) or not body['id']
                    or not isinstance(body.get('commands'), dict)
                    or not isinstance(body.get('settings'), dict)
                    or body['settings'].get('external_web_access') not in (True, 'live')):
                return handler.reject(400, 'Explicit model and live search commands required')
        except (ValueError, UnicodeError):
            return handler.reject(400, 'Invalid search request')
        # Only trusted host configuration chooses the upstream endpoint. Public
        # page fetches happen at the provider, never on the benchmark host.
        endpoint = owner.endpoint.rsplit('/', 1)[0] + '/alpha/search'
        journal = NativeJournal(owner.directory / 'web' / uuid.uuid4().hex)
        journal.write('request', {'time': time.time(), 'body': body})
        capture = self.transcript.child('web/' + journal.root.name) if self.transcript else None
        if capture:
            capture.emit('web_request', {'commands': body['commands'], 'settings': body['settings'],
                                        'native_max_output_tokens': body.get('max_output_tokens')})
        with self.lock:
            try:
                headers = {**{k: handler.headers[k] for k in REQUEST_HEADERS if k in handler.headers},
                           **owner.headers(), 'Content-Type': 'application/json', 'Accept': 'application/json'}
                journal.write('dispatch', {'time': time.time(), 'automatic_retries': 0})
                with httpx.Client(timeout=httpx.Timeout(owner.seconds, connect=min(15, owner.seconds)),
                                  proxy=owner.network_proxy, follow_redirects=False, trust_env=False) as client:
                    response = client.post(endpoint, content=raw, headers=headers)
                status, data = response.status_code, response.content
                journal.write('http', {'status': status, 'time': time.time()})
                with (journal.root / 'response.raw').open('xb') as out:
                    out.write(data); out.flush(); os.fsync(out.fileno())
                journal.write('complete', {'http_status': status, 'upstream_result_known': True})
                if capture:
                    capture.emit('web_retrieval', {'http_status': status,
                        'commands': body['commands'], 'response_text': data.decode('utf-8', errors='replace'),
                        'capture_scope': 'Exact provider response; agent interpretation is recorded separately.'})
            except Exception as exc:
                # Exception strings may contain headers. Record only the type.
                journal.write('interrupted', {'type': type(exc).__name__, 'upstream_result_known': False})
                if capture:
                    capture.emit('web_error', {'type': type(exc).__name__, 'upstream_result_known': False})
                return handler.reject(502, 'Search transport interrupted; no automatic replay')
            try:
                handler.send_response(status)
                handler.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                for name in RESPONSE_HEADERS:
                    if value := response.headers.get(name):
                        handler.send_header(name, value)
                handler.end_headers()
                handler.sent = True
                handler.wfile.write(data); handler.wfile.flush()
                journal.write('delivery', {'state': 'write_completed', 'client_received': 'unknown'})
            except OSError:
                journal.write('delivery', {'state': 'write_failed', 'client_received': 'unknown'})
