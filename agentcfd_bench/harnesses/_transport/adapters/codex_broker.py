"""Credential boundary and durable, per-request budget for Codex CLI.

Only a Unix socket is exposed to the namespace. No general HTTP proxy, redirects,
model fallback, invisible retries, or access to evaluator state is provided.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import socketserver
import threading
import time

import httpx
from ..journal import NativeJournal


def remove_empty_assistant_text(items, audit=None):
    """Drop only semantically empty assistant text, never tool or reasoning data.

    A provider can return an empty assistant message alongside real tool calls.
    Codex faithfully sends that message back, while some Chat gateways reject it.
    Whitespace, annotations, unknown fields and empty tool outputs are meaningful
    or opaque here and are preserved. The original request is never mutated.
    """
    if not isinstance(items, list):
        return items
    result = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get('role') != 'assistant' or item.get('type', 'message') != 'message':
            result.append(item)
            continue
        content = item.get('content')
        removed = []
        if isinstance(content, list):
            kept = []
            for block_index, block in enumerate(content):
                empty = (isinstance(block, dict) and block.get('type') in ('output_text', 'input_text')
                         and 'text' in block and block['text'] in ('', None)
                         and set(block) <= {'type', 'text', 'annotations', 'logprobs'}
                         and not block.get('annotations') and not block.get('logprobs'))
                if empty:
                    removed.append(block_index)
                else:
                    kept.append(block)
            cleaned = {**item, 'content': kept} if removed else item
            empty_content = not kept
        else:
            cleaned = item
            empty_content = 'content' in item and content in ('', None)
        # IDs/status are transport metadata. Unknown message fields must survive.
        remove_message = empty_content and set(item) <= {'type', 'role', 'content', 'id', 'status'}
        if not remove_message:
            result.append(cleaned)
        if audit is not None and (removed or remove_message):
            audit.append({'item_index': index, 'removed_text_blocks': removed, 'removed_message': remove_message})
    return result


def canonical_tool_history(items, *, normalization=None):
    """Make complete tool exchanges contiguous, omitting only empty text.

    Responses permits assistant commentary between a call and its result. Some
    Responses->Chat gateways reject that valid sequence. Move that commentary
    before its call group, preserving call IDs, outputs and all content verbatim.
    Never invent missing outputs or remove reasoning. ``normalization`` receives
    an index-only audit of the narrow empty-text cleanup, if requested.
    """
    if not isinstance(items, list):
        return items
    result, group, pending = [], [], set()
    for item in remove_empty_assistant_text(items, normalization):
        kind = item.get('type')
        if kind == 'function_call':
            if item['call_id'] in pending:
                raise ValueError('Duplicate pending tool call')
            pending.add(item['call_id'])
            group.append(item)
        elif group:
            group.append(item)
            if kind == 'function_call_output':
                if item['call_id'] not in pending:
                    raise ValueError('Unmatched tool output')
                pending.remove(item['call_id'])
            if not pending:
                result.extend(x for x in group if x.get('type') not in ('function_call', 'function_call_output'))
                result.extend(x for x in group if x.get('type') == 'function_call')
                result.extend(x for x in group if x.get('type') == 'function_call_output')
                group = []
        else:
            result.append(item)
    if group:
        raise ValueError('Missing tool results; refusing to fabricate them')
    return result


def completed_response_events(response):
    """Lossless nonstream->SSE envelope, only for a real completed response."""
    if response.get('object') != 'response' or response.get('status') != 'completed' or response.get('error'):
        raise ValueError('Upstream response was not completed')
    return terminal_response_events(response)


def _has_submission_output(output):
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get('type') == 'function_call':
            return True
        if item.get('type') != 'message' or item.get('role') != 'assistant':
            continue
        content = item.get('content')
        if isinstance(content, str) and content.strip():
            return True
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict) or block.get('type') not in ('output_text', 'refusal'):
                continue
            value = block.get('text', block.get('refusal'))
            if isinstance(value, str) and value.strip():
                return True
    return False


def terminal_response_events(response):
    """Expose the real terminal status; partial tool calls are never executable.

    The original terminal response (including all partial output) is preserved.
    Item events are emitted only for completed responses, so incomplete/failed
    function calls cannot be mistaken for a completed tool invocation.
    """
    if not isinstance(response, dict) or response.get('object') != 'response':
        raise ValueError('Expected a Responses object')
    status = response.get('status')
    if status not in ('completed', 'incomplete', 'failed'):
        raise ValueError('Expected a terminal Responses status')
    if status == 'completed' and response.get('error'):
        raise ValueError('Completed response contains an error')
    if not isinstance(response.get('output', []), list):
        raise ValueError('Response output must be a list')
    if status == 'completed' and not _has_submission_output(response.get('output', [])):
        raise EmptyAssistantResponse('Completed response has no assistant text or tool calls')
    events = [{'type': 'response.created', 'response': {**response, 'output': [], 'status': 'in_progress'}}]
    for index, item in enumerate(response.get('output', [])):
        if status == 'completed':
            events.extend([{'type': 'response.output_item.added', 'output_index': index, 'item': item},
                           {'type': 'response.output_item.done', 'output_index': index, 'item': item}])
    events.append({'type': 'response.' + status, 'response': response})
    return b''.join(('data: ' + json.dumps(event) + '\n\n').encode() for event in events)


class EmptyAssistantResponse(ValueError):
    """A completed-but-empty upstream response is not a valid final submission."""


def effective_output_limit(body, configured=None):
    """Pass through the client's limit; optional ceiling is legacy replay only."""
    requested = body.get('max_output_tokens')
    if configured is not None and (type(configured) is not int or configured <= 0):
        raise ValueError('Invalid configured output token limit')
    if requested is not None and (type(requested) is not int or requested <= 0):
        raise ValueError('Invalid requested output token limit')
    if configured is None:
        return requested
    return min(requested, configured) if requested is not None else configured


class Broker:
    def __init__(self, directory, *, endpoint, credential, model, limit, seconds=600, stream=True, socket_path=None,
                 max_output_tokens=None, parameters=None, wire_api='responses', judge_schema=None,
                 documentation=None):
        effective_output_limit({}, max_output_tokens)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.endpoint = endpoint.rstrip('/') + ('/responses' if endpoint.rstrip('/').endswith('/v1') else '/v1/responses')
        if wire_api not in ('responses', 'chat') or (wire_api == 'chat' and stream):
            raise ValueError('Chat transport requires nonstream mode')
        self.wire_api = wire_api
        self.judge_schema = judge_schema
        if wire_api == 'chat':
            self.endpoint = endpoint.rstrip('/') + '/chat/completions'
        self.credential, self.model = credential, model
        self.limit, self.seconds, self.calls = limit, seconds, 0
        self.stream = stream
        self.max_output_tokens, self.parameters = max_output_tokens, parameters or {}
        self.errors = []
        self.budget_exhausted = False
        from ..documentation import Access
        self.docs = Access(self.directory/'documentation', documentation)
        self.socket_path = Path(socket_path) if socket_path else self.directory / 'broker.sock'
        if len(str(self.socket_path).encode()) >= 104:
            raise ValueError('Broker socket path too long')
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reject(self, status, message):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': {'message': message, 'type': 'invalid_request_error'}}).encode())

            def do_POST(self):
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    return self.reject(400, 'Invalid content length')
                if not 0 < size <= 16 * 1024 * 1024:
                    return self.reject(413, 'Invalid request size')
                try:
                    body = json.loads(self.rfile.read(size))
                except (ValueError, UnicodeError):
                    return self.reject(400, 'Invalid JSON')
                if self.path.startswith('/v1/docs/'):
                    return owner.docs_service.respond(self, self.path, body)
                if self.path != '/v1/responses':
                    return self.reject(403, 'Endpoint not allowed')
                if not isinstance(body, dict):
                    return self.reject(400, 'JSON object required')
                if body.get('model') != owner.model:
                    return self.reject(403, 'Model not allowed')
                tools = body.get('tools', [])
                if not isinstance(tools, list) or any(not isinstance(t, dict) or t.get('type') != 'function' for t in tools) or any(
                        body.get(k) for k in ('previous_response_id', 'conversation', 'background')):
                    return self.reject(403, 'Remote tools and external state are not allowed')
                normalization = []
                try:
                    ordered_input = canonical_tool_history(body.get('input', []), normalization=normalization)
                except (ValueError, KeyError, TypeError, AttributeError):
                    return self.reject(400, 'Incomplete tool history')
                try:
                    output_limit = effective_output_limit(body, owner.max_output_tokens)
                except ValueError:
                    return self.reject(400, 'Invalid max_output_tokens')
                if owner.errors:
                    return self.reject(400, 'Previous request failed; host review required, no automatic redispatch')
                if owner.calls >= owner.limit:
                    if not owner.budget_exhausted:
                        NativeJournal(owner.directory).write('budget_exhausted', {
                            'calls':owner.calls, 'limit':owner.limit, 'http_status':400,
                            'reason':'local_model_call_budget_exhausted', 'provider_dispatched':False})
                    owner.budget_exhausted = True
                    return self.reject(400, 'Benchmark model call budget exhausted')
                owner.calls += 1
                call = owner.calls
                journal = NativeJournal(owner.directory / f'call-{call:03d}')
                # fsync BEFORE sending: uncertain requests cannot be replayed.
                journal.write('request', {'time': time.time(), 'body': body})
                wire_body = {**body, **owner.parameters, 'stream': owner.stream, 'store': False,
                             'model': owner.model}
                if output_limit is None:
                    wire_body.pop('max_output_tokens', None)
                else:
                    wire_body['max_output_tokens'] = output_limit
                wire_body['input'] = ordered_input
                if owner.judge_schema is not None:
                    remaining = owner.limit - owner.calls
                    final_only = remaining < 2
                    notice = (f'Judge request budget: {remaining} requests remain after this one. '
                              'Finish promptly; do not exhaust the budget reading entire large files. ')
                    if final_only:
                        notice += ('No more tools: return final JSON now using available evidence. '
                                   'Use uncertain for unsupported judgments. JSON schema: ' + json.dumps(owner.judge_schema))
                        wire_body['tools'] = []
                        wire_body['tool_choice'] = 'none'
                        if owner.wire_api == 'chat':
                            wire_body['_judge_final_json'] = True
                        else:
                            wire_body['text'] = {'format': {'type': 'json_schema', 'name': 'judge',
                                                           'strict': True, 'schema': owner.judge_schema}}
                    wire_body['input'] = [*ordered_input, {'role': 'developer', 'content': notice}]
                    journal.write('judge_budget', {'remaining_after_request': remaining, 'final_only': final_only})
                if owner.wire_api == 'chat':
                    from .judge_chat import chat_request
                    try:
                        wire_body = chat_request(wire_body)
                    except (ValueError, KeyError, TypeError):
                        return self.reject(400, 'Unsupported Chat adapter input; no upstream request sent')
                journal.write('wire_request', {'body': wire_body})
                journal.write('request_adapter', {'version': 'empty-assistant-text-v1',
                    'normalization': normalization,
                    'output_limit': {'requested': body.get('max_output_tokens'),
                        'configured': owner.max_output_tokens, 'effective': output_limit,
                        'source': ('client' if output_limit is not None else 'provider_default') if owner.max_output_tokens is None
                                  else ('min_codex_and_experiment' if body.get('max_output_tokens') is not None else 'experiment')}})
                started = time.monotonic()
                sent_headers = False
                http_status = None
                upstream_result_known = False
                stage = 'upstream_request'

                def record_error(category, reason, error_type, **details):
                    evidence = {'call': call, 'category': category, 'reason': reason,
                        'stage': stage, 'type': error_type, 'http_status': http_status,
                        'upstream_result_known': upstream_result_known,
                        'retry_safety': 'known_result' if upstream_result_known else 'unknown_no_replay',
                        **details}
                    owner.errors.append(evidence)
                    # A terminal response can also fail delivery. Preserve each
                    # event without overwriting the first (causal) error receipt.
                    name = 'error' if not (journal.root / 'error.json').exists() else 'delivery_error'
                    journal.write(name, evidence)

                try:
                    with httpx.Client(timeout=owner.seconds, follow_redirects=False, trust_env=False) as client:
                        if not owner.stream:
                            response = client.post(owner.endpoint, json=wire_body,
                                headers={'Authorization': 'Bearer ' + owner.credential})
                            http_status = response.status_code
                            upstream_result_known = True
                            stage = 'evidence_persistence'
                            journal.write('http', {'status': http_status, 'time': time.time()})
                            with (journal.root / 'response.raw').open('xb') as output:
                                output.write(response.content)
                                output.flush()
                                os.fsync(output.fileno())
                            journal.write('complete', {'elapsed_seconds': time.monotonic() - started,
                                'status': http_status, 'transport': 'nonstream-to-sse-v2'})
                            stage = 'upstream_response'
                            if http_status != 200:
                                record_error('upstream_http_error', 'http_rejected', 'UpstreamHTTPError')
                                return self.reject(400, 'Upstream rejected request; original status saved in host evidence, no automatic replay')
                            stage = 'response_decode'
                            parsed = response.json()
                            if owner.wire_api == 'chat':
                                from .judge_chat import responses_result
                                parsed = responses_result(parsed)
                            if owner.judge_schema is not None and wire_body.get('tool_choice') == 'none' and any(
                                    x.get('type') == 'function_call' for x in parsed.get('output', [])):
                                parsed['status'] = 'incomplete'
                                parsed['incomplete_details'] = {'reason': 'judge_finalization_tool_violation'}
                            stage = 'response_adaptation'
                            event_bytes = terminal_response_events(parsed)
                            response_status = parsed['status']
                            if response_status != 'completed':
                                details = parsed.get('incomplete_details') or {}
                                supplied_reason = details.get('reason') if isinstance(details, dict) else None
                                reason = supplied_reason if supplied_reason in ('max_output_tokens', 'content_filter') else 'unspecified'
                                usage = parsed.get('usage') or {}
                                output_tokens = usage.get('output_tokens') if isinstance(usage, dict) else None
                                output_tokens = output_tokens if type(output_tokens) is int and output_tokens >= 0 else None
                                record_error('response_' + response_status, reason, 'UpstreamResponse' + response_status.title(),
                                    response_status=response_status, output_tokens=output_tokens,
                                    effective_output_limit=output_limit,
                                    suspected_output_limit=response_status == 'incomplete' and output_tokens is not None
                                                           and output_limit is not None and output_tokens >= output_limit)
                            stage = 'downstream_delivery'
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/event-stream')
                            self.end_headers()
                            sent_headers = True
                            self.wfile.write(event_bytes)
                            self.wfile.flush()
                            return
                        with client.stream('POST', owner.endpoint, json=wire_body,
                                headers={'Authorization': 'Bearer ' + owner.credential}) as response:
                            http_status = response.status_code
                            journal.write('http', {'status': http_status, 'time': time.time()})
                            if http_status != 200:
                                with (journal.root / 'response.raw').open('xb') as output:
                                    output.write(response.read())
                                    output.flush()
                                    os.fsync(output.fileno())
                                upstream_result_known = True
                                journal.write('complete', {'elapsed_seconds':time.monotonic()-started,
                                                          'status':http_status})
                                stage = 'upstream_response'
                                record_error('upstream_http_error', 'http_rejected', 'UpstreamHTTPError')
                                return self.reject(400, 'Upstream rejected request; original status saved in host evidence, no automatic replay')
                            self.send_response(response.status_code)
                            self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                            self.end_headers()
                            sent_headers = True
                            stage = 'upstream_stream'
                            with (journal.root / 'response.raw').open('xb') as output:
                                for chunk in response.iter_bytes():
                                    output.write(chunk)
                                    output.flush()
                                    self.wfile.write(chunk)
                                    self.wfile.flush()
                                os.fsync(output.fileno())
                            upstream_result_known = True
                            stage = 'evidence_persistence'
                            journal.write('complete', {'elapsed_seconds': time.monotonic() - started,
                                'status': response.status_code})
                            # HTTP EOF is not proof of a completed model turn.
                            # Preserve the real stream, but lock future dispatch
                            # on missing/failed/incomplete terminal responses too.
                            stage = 'response_adaptation'
                            from ..provider_outcome import response_problem
                            from ..telemetry import terminal_body
                            problem = response_problem(terminal_body((journal.root/'response.raw').read_text()))
                            if problem:
                                record_error('response_format_error', problem, 'UpstreamResponseInvalid')
                except Exception as exc:
                    # No exception text: URLs/headers may contain secrets.
                    if isinstance(exc, httpx.TimeoutException):
                        category, reason = 'upstream_timeout', 'response_timeout'
                    elif isinstance(exc, httpx.TransportError):
                        category, reason = 'upstream_transport_error', 'transport_interrupted'
                    elif stage in ('response_decode', 'response_adaptation'):
                        category = 'response_format_error'
                        reason = 'empty_assistant_response' if isinstance(exc, EmptyAssistantResponse) else 'invalid_upstream_response'
                    elif stage == 'downstream_delivery':
                        category, reason = 'downstream_delivery_error', 'delivery_interrupted'
                    else:
                        category, reason = 'broker_error', 'adapter_interrupted'
                    record_error(category, reason, type(exc).__name__)
                    journal.write('interrupted', {'call': call, 'type': type(exc).__name__,
                        'stage': stage, 'http_status': http_status, 'upstream_result_known': upstream_result_known})
                    if not sent_headers:
                        self.reject(400, 'Request failed (' + category + '); no automatic replay')

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
