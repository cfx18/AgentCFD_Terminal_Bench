"""Runs INSIDE the anonymous namespace. Contains no credential or grader logic."""
import fcntl
import argparse
import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import re
import socket
import struct
import subprocess
import sys
import threading

# The sandbox never supplies host authorization. Forward only protocol state.
REQUEST_HEADERS = ('openai-beta', 'session_id', 'x-codex-turn-metadata',
                   'x-codex-turn-state', 'x-codex-parent-thread-id', 'x-codex-client-request-id',
                   'x-stainless-retry-count')
RESPONSE_HEADERS = ('x-codex-turn-state', 'x-request-id', 'retry-after')


class UnixHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout if isinstance(self.timeout, (int, float)) else None)
        self.sock.connect('/api/broker.sock')


class Relay(BaseHTTPRequestHandler):
    timeout_seconds = 660
    def log_message(self, *args):
        pass

    def do_POST(self):
        conn = UnixHTTP('localhost', timeout=self.timeout_seconds)
        call_id, failed = None, False
        try:
            body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            headers = {k: self.headers[k] for k in REQUEST_HEADERS if k in self.headers}
            conn.request('POST', self.path, body, {**headers, 'Content-Type': 'application/json'})
            response = conn.getresponse()
            # Only the guarded custom broker sets this private delivery binding.
            # It is not forwarded to the model client or the external provider.
            call_id = response.getheader('X-AgentCFD-Call-ID')
            if not isinstance(call_id, str) or not re.fullmatch(r'call-[0-9]{3,}', call_id):
                call_id = None
            try:
                self.send_response(response.status)
                self.send_header('Content-Type', response.getheader('Content-Type', 'application/json'))
                for name in RESPONSE_HEADERS:
                    if value := response.getheader(name):
                        self.send_header(name, value)
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                if not call_id:
                    raise
                failed = True
            while data := response.read1(65536):
                if not failed:
                    try:
                        self.wfile.write(data)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        if not call_id:
                            raise
                        failed = True
                # Still drain the known response, so a client disconnect never
                # interrupts the host's evidence collection.
        except (OSError, http.client.HTTPException):
            if not call_id:
                raise
            failed = True
        finally:
            conn.close()
        if call_id:
            delivery = UnixHTTP('localhost', timeout=self.timeout_seconds)
            try:
                body = json.dumps({'call_id': call_id, 'failed': failed}).encode()
                delivery.request('POST', '/internal/relay-delivery', body, {'Content-Type': 'application/json'})
                result = delivery.getresponse()
                result.read()
                if result.status != 200:
                    raise RuntimeError('Delivery observation was not recorded')
            finally:
                delivery.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--relay-timeout', type=float, default=660)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if args.relay_timeout <= 0 or not command:
        parser.error('Positive relay timeout and child command required')
    Relay.timeout_seconds = args.relay_timeout
    # Only this new network namespace is modified; no host network is shared.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        fcntl.ioctl(control, 0x8914, struct.pack('16sh', b'lo', 0x1 | 0x40))
    # Accept simultaneous CLI/subagent connections; the host separately enforces
    # paid-request concurrency. Do not fabricate SSE before upstream headers.
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Relay)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    environment = {'PATH': '/usr/bin:/bin', 'HOME': '/home/agent',
                   'CODEX_HOME': '/home/agent', 'LANG': 'C.UTF-8', 'TERM': 'dumb'}
    child = subprocess.Popen(command, env=environment)
    try:
        return child.wait()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    raise SystemExit(main())
