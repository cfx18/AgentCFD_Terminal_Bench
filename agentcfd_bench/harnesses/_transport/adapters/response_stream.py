"""Incremental SSE framing and response facts; never change model wire bytes."""
import json
import re


class Decoder:
    def __init__(self):
        self.pending = b''

    def feed(self, chunk):
        self.pending += chunk
        while match := re.search(rb'\r?\n\r?\n', self.pending):
            raw, self.pending = self.pending[:match.start()], self.pending[match.end():]
            data = '\n'.join(line[5:].removeprefix(' ') for line in
                             raw.decode('utf-8').splitlines() if line.startswith('data:'))
            if data and data != '[DONE]':
                value = json.loads(data)
                if not isinstance(value, dict):
                    raise ValueError('Non-object response event')
                yield value


class ResponseFacts:
    TERMINALS = {'response.completed': 'completed', 'response.failed': 'failed',
                 'response.incomplete': 'incomplete'}

    def __init__(self, model):
        self.model = model
        self.reported_models = set()
        self.terminal = None

    def observe(self, event):
        body = event.get('response')
        if isinstance(body, dict) and body.get('model') is not None:
            if not isinstance(body['model'], str) or not body['model']:
                raise ValueError('Invalid reported model identity')
            self.reported_models.add(body['model'])
        expected_status = self.TERMINALS.get(event.get('type'))
        if expected_status:
            if not isinstance(body, dict) or body.get('status') != expected_status:
                raise ValueError('Terminal event/status mismatch')
            self.terminal = body

    @property
    def model_matches(self):
        return bool(self.reported_models) and all(
            v.casefold() == self.model.casefold() for v in self.reported_models)

    @property
    def model_mismatch(self):
        return any(v.casefold() != self.model.casefold() for v in self.reported_models)
