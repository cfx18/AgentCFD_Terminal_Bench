"""Host-only explicit-model broker: immutable receipts, bounded calls, no retries."""
import asyncio
import json
import hashlib
import os
from pathlib import Path
import socketserver
import threading
import time
import re
from http.server import BaseHTTPRequestHandler

import httpx

from ..journal import NativeJournal, read_receipt
from . import protocol


async def receive_response(endpoint, credential, wire, seconds, journal):
    """Bound the entire HTTP exchange, including a continuously dripping body.

    HTTPX's read timeout alone restarts on every chunk. Keep partial bytes as
    evidence, but never mark a deadline/cancelled response complete or retry it.
    """
    received, status, complete = 0, None, False
    started = time.monotonic()
    try:
        async with asyncio.timeout(seconds):
            async with httpx.AsyncClient(timeout=seconds, trust_env=False,
                                         follow_redirects=False) as client:
                async with client.stream('POST', endpoint.rstrip('/') + '/chat/completions',
                        json=wire, headers={'Authorization': 'Bearer ' + credential}) as response:
                    status = response.status_code
                    journal.write('http', {'status': status})
                    chunks = []
                    with (journal.root / 'response.raw').open('xb') as out:
                        try:
                            async for chunk in response.aiter_bytes():
                                out.write(chunk)
                                out.flush()
                                received += len(chunk)
                                chunks.append(chunk)
                        finally:
                            out.flush()
                            os.fsync(out.fileno())
                    complete = True
                    return httpx.Response(status, content=b''.join(chunks),
                                          request=response.request)
    except TimeoutError as exc:
        raise httpx.ReadTimeout('Total provider request deadline exceeded') from exc
    finally:
        journal.write('stream_closed', {'transport_closed': True,
            'http_status': status, 'received_bytes': received,
            'response_body_complete': complete, 'deadline_seconds': seconds,
            'elapsed_seconds': time.monotonic() - started})


class Broker:
    def __init__(self, root, socket_path, *, endpoint, credential, limit, seconds=600, cap=None,
                 documentation=None, model='Kimi-K3', transcript=None, guard_retries=False,
                 native_chat=False):
        if not isinstance(model, str) or not model.strip():
            raise ValueError('Explicit provider model required')
        self.directory = Path(root)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.socket_path = Path(socket_path)
        self.calls, self.errors, self.budget_exhausted = 0, [], False
        from ..documentation import Access
        self.docs = Access(self.directory/'documentation', documentation, transcript=transcript)
        owner = self
        pending_bodies = {}
        retry_rejections = 0
        adapter_rejections = 0

        def delivery(body):
            if (not guard_retries or not isinstance(body, dict) or set(body) != {'call_id', 'failed'}
                    or not isinstance(body['call_id'], str) or not re.fullmatch(r'call-[0-9]{3,}', body['call_id'])
                    or type(body['failed']) is not bool):
                raise ValueError('Invalid delivery observation')
            call_root = owner.directory/body['call_id']
            if read_receipt(call_root/'complete.json') is None:
                raise ValueError('Delivery lacks a completed upstream response')
            journal = NativeJournal(call_root)
            record = {'stage': 'relay_to_client', 'state': 'write_failed' if body['failed'] else 'write_completed',
                      'client_received': 'unknown', 'known_response': True}
            name = 'relay_delivery'
            previous = journal.read(name)
            if previous is None:
                journal.write(name, record)
            elif previous != record:
                raise ValueError('Delivery observation changed')
            # Preserve the earliest failure if both transport hops failed.
            outcome = 'delivery_error' if body['failed'] else 'delivery'
            if journal.read(outcome) is None:
                journal.write(outcome, record)
            if body['failed']:
                owner.errors.append({'type': 'RelayDeliveryError', 'reason': 'provider_delivery_failed',
                                     'known_response': True, 'call_id': body['call_id']})
            if transcript:
                transcript.child('api/'+body['call_id']).emit('provider_delivery', record)

        def reject_retry(reason, signature):
            nonlocal retry_rejections
            retry_rejections += 1
            record = {'reason': reason, 'wire_hash': signature, 'provider_dispatched': False}
            NativeJournal(owner.directory/'retry_rejections').write(f'{retry_rejections:03d}', record)
            owner.errors.append({'type': 'ClientRetryRejected', **record})
            if transcript:
                transcript.emit('provider_error', record)

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                self.request.settimeout(min(seconds + 10, 30))
                super().setup()

            def log_message(self, *args):
                pass

            def send(self, status, body, mime='application/json', call_id=None):
                self.send_response(status)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(body)))
                if call_id is not None:
                    self.send_header('X-AgentCFD-Call-ID', call_id)
                self.end_headers()
                self.wfile.write(body)

            def reject(self, status, message, error_type='api_error'):
                self.send(status, json.dumps({'type': 'error', 'error': {'type': error_type, 'message': message}}).encode())

            def do_POST(self):
                nonlocal adapter_rejections
                path = self.path.split('?', 1)[0]
                body = None
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 16 * 1024 * 1024:
                        raise ValueError('Request size rejected')
                    body = json.loads(self.rfile.read(size))
                    if path == '/internal/relay-delivery':
                        delivery(body)
                        return self.send(200, b'{}')
                    if path.startswith('/v1/docs/'):
                        return owner.docs_service.respond(self, path, body)
                    wire = protocol.request(path, body, model, cap)
                    if native_chat:
                        if path != '/v1/chat/completions' or cap is not None:
                            raise ValueError('Native Chat transport cannot translate another protocol')
                        # Keep the CLI's sampling/thinking/history settings. Only
                        # transport changes: receive complete JSON, relay as SSE.
                        wire = {**body, 'stream': False}
                        wire.pop('stream_options', None)
                except (ValueError, KeyError, TypeError, AttributeError) as exc:
                    adapter_rejections += 1
                    NativeJournal(owner.directory/'adapter-rejections').write(f'{adapter_rejections:04d}',
                        {'path':path,'body':body,'error':str(exc),'provider_dispatched':False})
                    owner.errors.append({'type': type(exc).__name__, 'reason': str(exc), 'stage': 'request_adapter', 'dispatch': False})
                    return self.reject(400, 'Unsupported client request; see host adapter evidence')
                signature = hashlib.sha256(json.dumps(wire, sort_keys=True).encode()).hexdigest()
                if guard_retries:
                    retry = self.headers.get('x-stainless-retry-count', '0')
                    original = pending_bodies.get(signature)
                    unconfirmed = original and not (owner.directory/original/'delivery.json').exists()
                    if retry != '0' or unconfirmed:
                        reject_retry('client_retry_rejected' if retry != '0' else 'unconfirmed_request_replay_rejected', signature)
                        return self.reject(400, 'Existing request must be resolved; no automatic upstream retry', 'invalid_request_error')
                if owner.errors:
                    # The session is fail-closed. A retryable HTTP status
                    # would invite SDK backoff without any allowed dispatch.
                    return self.reject(400, 'Previous request failed; host review required, no automatic redispatch', 'invalid_request_error')
                if owner.calls >= limit:
                    if not owner.budget_exhausted:
                        NativeJournal(owner.directory).write('budget_exhausted', {
                            'calls': owner.calls, 'limit': limit, 'http_status': 400,
                            'reason': 'local_model_call_budget_exhausted', 'provider_dispatched': False})
                    owner.budget_exhausted = True
                    # This cannot recover by waiting. A retryable 429 makes
                    # real clients back off for minutes after all paid work has
                    # finished. Keep genuine upstream errors separate.
                    return self.reject(400, 'Benchmark request budget exhausted', 'invalid_request_error')
                owner.calls += 1
                journal = NativeJournal(owner.directory / f'call-{owner.calls:03d}')
                if guard_retries:
                    pending_bodies[signature] = journal.root.name
                journal.write('request', {'path': path, 'body': body})
                journal.write('wire_request', {'body': wire})
                journal.write('dispatch', {'time': time.time()})
                capture = transcript.child(f'api/call-{owner.calls:03d}') if transcript else None
                if capture:
                    capture.emit('provider_request', {'path': path, 'client_body': body, 'wire_body': wire})
                started = time.monotonic()
                known = False
                try:
                    result = asyncio.run(receive_response(endpoint, credential, wire, seconds, journal))
                    known = True
                    journal.write('complete', {'elapsed_seconds': time.monotonic() - started, 'status': result.status_code})
                    # Capture before adaptation: even a rejected length/format
                    # response remains reviewable, without executing its tools.
                    if capture:
                        try:
                            payload = result.json()
                        except ValueError:
                            payload = {'text': result.text}
                        capture.emit('provider_response', {'status': result.status_code, 'body': payload})
                    if result.status_code != 200:
                        raise ValueError('upstream_http_' + str(result.status_code))
                    parsed = result.json()
                    if parsed.get('model', '').casefold() != model.casefold():
                        raise ValueError('Returned model identity mismatch')
                    mime, data = protocol.response(path, parsed, body.get('stream', False))
                    journal.write('adapted', {'content_type': mime, 'bytes': len(data)})
                    self.send(200, data, mime, journal.root.name if guard_retries else None)
                    if capture:
                        capture.emit('provider_delivery', {'state': 'write_completed', 'client_received': 'unknown',
                                                          'stage': 'broker_to_relay'})
                except Exception as exc:
                    error = {'type': type(exc).__name__, 'reason': str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                             'known_response': known, 'call': owner.calls}
                    from ..diagnostics import exception_record
                    error['diagnostic'] = exception_record(exc, secrets=(credential,))
                    if hasattr(exc, "provider_failure"):
                        error["provider_failure"] = exc.provider_failure
                        error["finish_reason"] = exc.finish_reason
                    owner.errors.append(error)
                    journal.write('error', error)
                    if guard_retries and known and isinstance(exc, (BrokenPipeError, ConnectionResetError)):
                        journal.write('delivery_error', {'stage':'broker_to_relay', 'state':'write_failed',
                                                        'client_received':'unknown', 'known_response':True})
                    if capture:
                        capture.emit('provider_error', error)
                    try:
                        # Local terminal status; original upstream status and
                        # known/unknown outcome remain in the host journal.
                        self.reject(400, 'Provider/adapter request failed; original evidence saved on host, no automatic redispatch', 'invalid_request_error')
                    except OSError:
                        pass

        self.server = socketserver.UnixStreamServer(str(self.socket_path), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        try:
            self.docs_service = DocumentationService(self.docs, self.socket_path.with_name("docs.sock"))
        except BaseException:
            self.server.server_close()
            raise

    def __enter__(self):
        self.docs_service.start()
        try:
            self.thread.start()
        except BaseException:
            self.server.server_close()
            self.docs_service.close()
            raise
        return self

    def __exit__(self, *args):
        try:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
        finally:
            self.docs_service.close()

from ..documentation_service import DocumentationService
