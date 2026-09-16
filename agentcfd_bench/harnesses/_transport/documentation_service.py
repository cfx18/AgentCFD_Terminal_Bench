"""Private candidate: one dedicated read-only docs worker, no model access.

The model broker retains its original single worker. A lock covers Access and
its transport record because the old docs route may also delegate here.
"""
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import socketserver
import threading
import time

from agentcfd_bench.harnesses._transport.identity import fingerprint
from agentcfd_bench.harnesses._transport.journal import NativeJournal, read_receipt
from agentcfd_bench.harnesses._transport.documentation import usage as generated_usage

VERSION = 'dedicated-docs-transport-v1'


class DocumentationService:
    def __init__(self, access, socket_path):
        self.access, self.socket_path = access, Path(socket_path)
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                self.request.settimeout(30)
                super().setup()

            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 16*1024*1024:
                        raise ValueError('Request size rejected')
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise ValueError('Incomplete request')
                    body = json.loads(raw)
                except (ValueError, UnicodeError, OSError):
                    # No raw malformed content or host exception text is exposed.
                    body = None
                owner.respond(self, self.path.split('?',1)[0], body)

        self.server = socketserver.UnixStreamServer(str(self.socket_path), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def respond(self, handler, path, body):
        with self.lock:
            journal = NativeJournal(self.access.root/f'query-{self.access.calls+1:04d}')
            journal.write('transport_started', {'version':VERSION, 'time':time.time()})
            status, value = self.access.request(path, body)
            encoded = json.dumps(value, allow_nan=False).encode()
            result = {'version':VERSION, 'response_hash':fingerprint({'status':status,'body':value}),
                      'client_received':'unknown', 'time':time.time()}
            try:
                handler.send_response(status)
                handler.send_header('Content-Type','application/json')
                handler.send_header('Content-Length',str(len(encoded)))
                handler.end_headers()
                handler.wfile.write(encoded)
                handler.wfile.flush()
            except OSError as exc:
                result.update(state='write_failed', error_type=type(exc).__name__)
            else:
                result.update(state='write_completed', bytes=len(encoded))
            # This is write evidence, not a claim that the agent read the body.
            journal.write('transport', result)
            if self.access.transcript:
                self.access.transcript.child(f'docs/query-{self.access.calls:04d}').emit(
                    'docs_delivery', {k: v for k, v in result.items() if k != 'response_hash'})

    def start(self):
        self.thread.start()

    def close(self):
        if self.thread.is_alive():
            self.server.shutdown()
        self.server.server_close()
        if self.thread.ident is not None:
            self.thread.join()


def transport_usage(root):
    """Read old/new evidence without inventing delivery for historical records."""
    result = generated_usage(root)
    if result is None:
        return None
    result['response_characters_generated'] = result.pop('returned_characters')
    result.update(transport_writes_completed=0, transport_writes_failed=0,
                  transport_unknown=0, client_receipt_unknown=result['queries'])
    for path in sorted(Path(root).glob('query-*')):
        transport = read_receipt(path/'transport.json')
        if transport is None:
            result['transport_unknown'] += 1
            continue
        response = read_receipt(path/'response.json')
        if (transport.get('version') != VERSION or response is None
                or transport.get('response_hash') != fingerprint(response)
                or transport.get('client_received') != 'unknown'):
            raise ValueError('Documentation transport/response binding mismatch')
        state = transport.get('state')
        if state == 'write_completed':
            result['transport_writes_completed'] += 1
        elif state == 'write_failed':
            result['transport_writes_failed'] += 1
        else:
            raise ValueError('Unknown documentation transport state')
    return result
