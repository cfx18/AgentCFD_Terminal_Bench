"""Host Responses relay: serial paid dispatch, concurrent observable waiters.

Provider completion, downstream delivery and client tool execution are distinct.
No model fallback, retries, history conversion or benchmark output-token cap.
"""
from http.server import BaseHTTPRequestHandler
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socketserver
import threading
import time
import uuid

import httpx

from ..documentation import Access
from ..documentation_service import DocumentationService
from ..journal import NativeJournal
from ..live_transcript import StreamCapture
from .codex_bridge import REQUEST_HEADERS, RESPONSE_HEADERS
from .request_queue import SerialRequests, QueueCancelled
from .response_stream import Decoder, ResponseFacts
from ..diagnostics import exception_record


@contextmanager
def durable_response(path):
    """A disconnected stream is still evidence, including its partial tail."""
    with path.open('xb') as out:
        try:
            yield out
        finally:
            out.flush()
            os.fsync(out.fileno())


def local_tools(tools, *, allow_web_search=False):
    if not isinstance(tools, list):
        return False
    for tool in tools:
        if not isinstance(tool, dict):
            return False
        if tool.get('type') == 'namespace':
            if not local_tools(tool.get('tools'), allow_web_search=allow_web_search):
                return False
        elif allow_web_search and tool.get('type') in ('web_search', 'web_search_preview'):
            continue  # Provider-hosted public research, not shell network access.
        elif tool.get('type') not in ('function', 'custom'):
            return False
    return True


def local_request_tools(body, *, allow_web_search=False):
    """New CLI versions embed tool declarations in additional_tools input items."""
    return local_tools(body.get('tools', []), allow_web_search=allow_web_search) and all(
        local_tools(item.get('tools'), allow_web_search=allow_web_search) for item in body.get('input', [])
        if isinstance(item, dict) and item.get('type') == 'additional_tools')


class Broker:
    def __init__(self, directory, socket_path, *, headers, endpoint, model, limit,
                 seconds=600, documentation=None, network_proxy=None, transcript=None,
                 queue_poll_seconds=0.1, allow_web_search=False):
        if type(limit) is not int or limit < 1 or seconds <= 0 or queue_poll_seconds <= 0:
            raise ValueError('Positive request budget and transport guards required')
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.endpoint, self.headers = endpoint, headers
        self.model, self.limit, self.seconds = model, limit, seconds
        self.network_proxy = network_proxy
        self.allow_web_search = allow_web_search
        self.calls, self.errors, self.budget_exhausted = 0, [], False
        self.queue = SerialRequests()
        self.socket_path = Path(socket_path)
        self.docs = Access(self.directory/'documentation', documentation, transcript=transcript)
        self.docs_service = DocumentationService(self.docs, self.socket_path.with_name('docs.sock'))
        owner = self
        from .web_research import WebResearch
        web_research = WebResearch(self, transcript)

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                self.request.settimeout(min(seconds+10, 30))
                super().setup()

            def log_message(self, *args):
                pass

            def reject(self, status, message):
                # After a stream starts, use an error event instead of a second
                # HTTP header. Queueing itself does NOT send premature headers.
                if self.sent:
                    data = 'data: '+json.dumps({'type': 'error', 'code': 'benchmark_request_rejected',
                                              'message': message})+'\n\n'
                    self.wfile.write(data.encode())
                    self.wfile.flush()
                else:
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': {'message': message,
                        'type': 'invalid_request_error'}}).encode())

            def stream_headers(self, response_headers=None):
                if self.sent:
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                if response_headers:
                    for name in RESPONSE_HEADERS:
                        if value := response_headers.get(name):
                            self.send_header(name, value)
                self.end_headers()
                self.sent = True

            def do_POST(self):
                self.sent = False
                if self.path == '/v1/alpha/search':
                    return web_research.handle(self)
                if self.path != '/v1/responses':
                    return self.reject(403, 'Endpoint not allowed')
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 16*1024*1024:
                        return self.reject(413, 'Invalid request size')
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise ValueError('Incomplete request')
                    body = json.loads(raw)
                except (ValueError, UnicodeError):
                    return self.reject(400, 'Invalid request')
                if not isinstance(body, dict) or body.get('model') != owner.model:
                    return self.reject(403, 'Explicit model required; fallback forbidden')
                if (not local_request_tools(body, allow_web_search=owner.allow_web_search) or body.get('stream') is not True
                        or body.get('store') is not False or any(body.get(k) for k in
                        ('previous_response_id', 'conversation', 'background'))):
                    return self.reject(403, 'Only native streaming, configured tools and isolated history allowed')
                incoming = NativeJournal(owner.directory/'incoming'/uuid.uuid4().hex)
                incoming.write('received', {'time': time.time(), 'body': body})
                queued = False

                def waiting(elapsed):
                    nonlocal queued
                    if not queued:
                        incoming.write('queued', {'time': time.time(), 'provider_concurrency': 1})
                        queued = True
                    try:
                        if owner.errors:
                            self.reject(400, 'Previous request failed; no automatic redispatch')
                            incoming.write('cancelled', {'reason': 'previous_request_failed', 'provider_dispatched': False})
                            return False
                        if elapsed >= owner.seconds:
                            self.reject(408, 'Local request queue timed out before provider dispatch')
                            incoming.write('cancelled', {'reason': 'local_queue_timeout', 'provider_dispatched': False})
                            return False
                        return True
                    except OSError as exc:
                        incoming.write('cancelled', {'reason': 'queued_client_disconnected',
                            'type': type(exc).__name__, 'provider_dispatched': False})
                        return False

                try:
                    with owner.queue.admit(waiting, interval=queue_poll_seconds) as elapsed:
                        incoming.write('admitted', {'time': time.time(), 'queue_seconds': elapsed})
                        self.dispatch(body, raw, incoming, elapsed)
                except QueueCancelled:
                    pass

            def dispatch(self, body, raw, incoming, queued_seconds):
                # Only one admitted request enters here. Budget/auth/terminal
                # receipts cannot race; queued requests are not paid dispatches.
                if owner.errors:
                    incoming.write('cancelled', {'reason': 'previous_request_failed', 'provider_dispatched': False})
                    return self.reject(400, 'Previous request failed; no automatic redispatch')
                if owner.calls >= owner.limit:
                    if not owner.budget_exhausted:
                        NativeJournal(owner.directory).write('budget_exhausted', {
                            'calls': owner.calls, 'limit': owner.limit, 'provider_dispatched': False})
                    owner.budget_exhausted = True
                    incoming.write('cancelled', {'reason': 'model_call_budget_exhausted', 'provider_dispatched': False})
                    return self.reject(400, 'Benchmark model call budget exhausted')
                try:
                    headers = owner.headers()
                except Exception as exc:
                    error = {'type': type(exc).__name__, 'reason': 'subscription_auth_unavailable'}
                    owner.errors.append(error)
                    NativeJournal(owner.directory).write('auth_error', error)
                    return self.reject(401, 'Subscription authentication unavailable; no request sent')
                owner.calls += 1
                journal = NativeJournal(owner.directory/f'call-{owner.calls:03d}')
                journal.write('request', {'time': time.time(), 'body': body})
                journal.write('wire_request', {'body': body})
                journal.write('request_adapter', {'version': 'native-responses-verbatim-v2',
                    'normalization': [], 'output_limit': {'requested': body.get('max_output_tokens'),
                        'configured': None, 'effective': body.get('max_output_tokens')},
                    'network_proxy': owner.network_proxy, 'connect_timeout_seconds': min(15, owner.seconds),
                    'web_search_allowed': owner.allow_web_search,
                    'queue_seconds': queued_seconds, 'provider_concurrency': 1})
                incoming.write('dispatch', {'call': journal.root.name, 'time': time.time()})
                capture = transcript.child(f'api/{journal.root.name}') if transcript else None
                stream_capture = StreamCapture(capture) if capture else None
                if capture:
                    capture.emit('provider_request', {'path': self.path, 'body': body,
                                                      'queue_seconds': queued_seconds})
                started, known, delivered, status = time.monotonic(), False, True, None
                facts, decoder = ResponseFacts(owner.model), Decoder()
                unverified = b''
                received_bytes, event_count, last_event = 0, 0, None

                def error(name, value):
                    owner.errors.append(value)
                    journal.write(name, value)
                    if capture:
                        capture.emit('provider_error', value)

                def delivery_failed(exc):
                    nonlocal delivered
                    if delivered:
                        delivered = False
                        error('delivery_error', {'type': type(exc).__name__, 'reason': 'provider_delivery_failed',
                                                'client_received': 'unknown'})

                try:
                    headers = {**{k: self.headers[k] for k in REQUEST_HEADERS if k in self.headers},
                               **headers, 'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
                    timeout = httpx.Timeout(owner.seconds, connect=min(15, owner.seconds))
                    journal.write('dispatch', {'time': time.time()})
                    with httpx.Client(timeout=timeout, proxy=owner.network_proxy,
                                      follow_redirects=False, trust_env=False) as client:
                        with client.stream('POST', owner.endpoint, content=raw, headers=headers) as response:
                            status = response.status_code
                            journal.write('http', {'status': status, 'time': time.time(),
                                'protocol_headers': {k: response.headers[k] for k in RESPONSE_HEADERS if k in response.headers}})
                            if status != 200:
                                response_body = response.read()
                                with (journal.root/'response.raw').open('xb') as out:
                                    out.write(response_body); out.flush(); os.fsync(out.fileno())
                                known = True
                                journal.write('complete', {'status': status, 'http_status': status,
                                    'elapsed_seconds': time.monotonic()-started})
                                error('error', {'reason': 'provider_http_error', 'http_status': status})
                                if capture:
                                    capture.emit('provider_response', {'status': status,
                                        'text': response_body.decode('utf-8', errors='replace')})
                                try:
                                    self.send_response(status)
                                    self.send_header('Content-Type', response.headers.get('content-type','application/json'))
                                    for name in RESPONSE_HEADERS:
                                        if value := response.headers.get(name):
                                            self.send_header(name, value)
                                    self.end_headers()
                                    self.sent = True
                                    self.wfile.write(response_body); self.wfile.flush()
                                except OSError as exc:
                                    delivery_failed(exc)
                                return
                            try:
                                self.stream_headers(response.headers)
                            except OSError as exc:
                                delivery_failed(exc)
                            with durable_response(journal.root/'response.raw') as out:
                                for chunk in response.iter_bytes():
                                    out.write(chunk); out.flush()
                                    received_bytes += len(chunk)
                                    if stream_capture:
                                        stream_capture.feed(chunk)
                                    for event in decoder.feed(chunk):
                                        event_count += 1
                                        last_event = event.get('type')
                                        facts.observe(event)
                                        if facts.terminal is not None:
                                            break
                                    if facts.terminal is not None:
                                        # Persist terminal evidence BEFORE the
                                        # completion receipt and client write.
                                        os.fsync(out.fileno())
                                        journal.write('complete', {'status': status,
                                            'response_status': facts.terminal['status'],
                                            'reported_models': sorted(facts.reported_models),
                                            'model_identity_verified': facts.model_matches,
                                            'elapsed_seconds': time.monotonic()-started,
                                            'transport': 'native-sse-verbatim-v2'})
                                        known = True
                                    unverified += chunk
                                    if delivered and facts.model_matches:
                                        try:
                                            self.wfile.write(unverified); self.wfile.flush()
                                            unverified = b''
                                        except OSError as exc:
                                            delivery_failed(exc)
                                    if not delivered or facts.model_mismatch:
                                        unverified = b''
                                    if known:
                                        break  # Protocol terminal, not TCP EOF.
                                os.fsync(out.fileno())
                    if not known:
                        error('interrupted', {'reason': 'model_request_outcome_unresolved', 'upstream_result_known': False})
                    elif not facts.model_matches:
                        error('error', {'reason': 'provider_model_identity_error',
                            'expected_model': owner.model, 'reported_models': sorted(facts.reported_models),
                            'upstream_result_known': True})
                        if delivered:
                            try:
                                self.reject(400, 'Returned model identity missing or different; no fallback allowed')
                            except OSError as exc:
                                delivery_failed(exc)
                    elif facts.terminal['status'] != 'completed' or facts.terminal.get('error'):
                        error('error', {'reason': 'provider_response_failed', 'upstream_result_known': True})
                except Exception as exc:
                    error('interrupted', {**exception_record(exc, secrets=tuple(headers.values())),
                        'reason': 'provider_transport_or_protocol_error',
                        'http_status': status, 'upstream_result_known': known})
                    if not self.sent:
                        try:
                            self.reject(502, 'Transport interrupted; no automatic replay')
                        except OSError as delivery_exc:
                            delivery_failed(delivery_exc)
                finally:
                    # This proves the local upstream transport has been closed,
                    # NOT that the provider completed or cancelled generation.
                    journal.write('stream_closed', {'transport_closed': True,
                        'upstream_result_known': known, 'http_status': status,
                        'received_bytes': received_bytes, 'complete_events': event_count,
                        'last_event_type': last_event, 'partial_event_bytes': len(decoder.pending)})
                    delivery = {'state': ('write_failed' if not delivered else
                                         'write_completed' if known else 'partial_or_unknown'),
                                'upstream_result_known': known, 'client_received': 'unknown'}
                    journal.write('delivery', delivery)
                    if capture:
                        capture.emit('provider_delivery', delivery)
                    if stream_capture:
                        stream_capture.finish()

        try:
            self.server = socketserver.ThreadingUnixStreamServer(str(self.socket_path), Handler)
        except BaseException:
            self.docs_service.close()
            raise
        # Non-daemon workers are joined: collect already dispatched outcomes.
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.docs_service.start()
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.docs_service.close()
