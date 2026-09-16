"""Host-only ChatGPT credential access. Never mounted into an evaluated workspace.

The official Codex auth manager owns refresh/login. This module does not implement
OAuth, write auth.json, log tokens, or fall back to an API key/custom endpoint.
"""
import base64
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
from urllib.parse import urlsplit

from ...codex import CODEX

ENDPOINT = 'https://chatgpt.com/backend-api/codex/responses'


class SubscriptionAuth:
    def __init__(self, home=None, network_proxy=None):
        self.home = Path(home or os.environ.get('CODEX_HOME') or Path.home()/'.codex').resolve()
        self.network_proxy = network_proxy or os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        if self.network_proxy:
            url = urlsplit(self.network_proxy)
            if (url.scheme not in ('http', 'https') or url.hostname not in ('127.0.0.1', 'localhost', '::1')
                    or url.username or url.password or url.query or url.fragment or url.path not in ('', '/')):
                raise ValueError('Subscription network proxy must be an explicit local CONNECT proxy')

    def _read(self):
        path = self.home/'auth.json'
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError('Subscription auth must be a private host file')
        value = json.loads(path.read_text())
        tokens = value.get('tokens') or {}
        if value.get('auth_mode') != 'chatgpt' or not all(
                isinstance(tokens.get(k), str) and tokens[k] for k in ('access_token', 'account_id')):
            raise ValueError('ChatGPT subscription login required; API key fallback is forbidden')
        return tokens

    def refresh(self):
        """Use the official account/read refresh path, without starting a model turn."""
        command = [str(CODEX), 'app-server', '--listen', 'stdio://']
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.home.parent), 'CODEX_HOME': str(self.home)}
        if self.network_proxy:
            env['HTTPS_PROXY'] = self.network_proxy
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, env=env, start_new_session=True, bufsize=0)
        def send(value):
            child.stdin.write((json.dumps(value)+'\n').encode())
            child.stdin.flush()
        def receive(identifier):
            deadline = time.monotonic()+45
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if not selector.select(max(0, deadline-time.monotonic())):
                        break
                    line = child.stdout.readline()
                    if not line:
                        break
                    event = json.loads(line)
                    if event.get('id') == identifier:
                        if 'error' in event:
                            raise RuntimeError('Official Codex authentication refresh rejected')
                        return event.get('result', {})
            raise RuntimeError('Official Codex authentication refresh did not complete')
        try:
            send({'id': 1, 'method': 'initialize', 'params': {
                'clientInfo': {'name': 'private-auth-refresh', 'version': '1'}}})
            receive(1)
            send({'method': 'initialized'})
            send({'id': 2, 'method': 'account/read', 'params': {'refreshToken': True}})
            result = receive(2)
            if (result.get('account') or {}).get('type') != 'chatgpt':
                raise RuntimeError('Official Codex did not confirm ChatGPT authentication')
        finally:
            # No model or tool turn was started. Do not leave an auth daemon behind.
            import signal
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            child.stdin.close()
            child.stdout.close()

    def headers(self):
        tokens = self._read()
        # JWT expiry is only a refresh hint, not proof of authentication. Opaque
        # access tokens remain valid inputs for the official service to validate.
        try:
            part = tokens['access_token'].split('.')[1]
            expiry = json.loads(base64.urlsafe_b64decode(part+'='*(-len(part)%4))).get('exp')
        except (ValueError, IndexError, UnicodeError):
            expiry = None
        if isinstance(expiry, (int, float)) and expiry < time.time()+180:
            self.refresh()
            tokens = self._read()
        return {'Authorization': 'Bearer '+tokens['access_token'],
                'ChatGPT-Account-Id': tokens['account_id'], 'originator': 'codex_cli_rs',
                'User-Agent': 'codex_cli_rs/0.153.4'}

    def catalog(self, model, effort):
        """Only public model metadata is copied, never auth or prior sessions."""
        value = json.loads((self.home/'models_cache.json').read_text())
        entries = [m for m in value['models'] if m.get('slug') == model]
        if len(entries) != 1 or effort not in {
                level['effort'] for level in entries[0]['supported_reasoning_levels']}:
            raise ValueError('Requested model/reasoning effort absent from local Codex catalog')
        return {'models': entries}
