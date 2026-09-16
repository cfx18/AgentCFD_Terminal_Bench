"""Text/function-only client protocols into one fixed Chat provider contract.

No default thinking/temperature overrides. Native thinking signatures and server
tools are not silently fabricated. Raw requests/responses remain in host journals.
"""
import json

from ..adapters.codex_broker import canonical_tool_history, terminal_response_events


def text(value):
    if isinstance(value, str):
        return value
    if value is None:
        return ''
    if not isinstance(value, list):
        raise ValueError('Text or text blocks required')
    if any(p.get('type') not in ('text', 'input_text', 'output_text') for p in value):
        raise ValueError('Nontext block unsupported')
    return ''.join(p.get('text', '') for p in value)


def request(path, body, model, cap=None):
    if not isinstance(body, dict) or body.get('model') != model:
        raise ValueError('Unexpected model; no model substitution allowed')
    if any(body.get(k) for k in ('previous_response_id', 'conversation', 'background')):
        raise ValueError('Remote state unsupported')
    messages, tools = [], []
    if path == '/v1/responses':
        if body.get('instructions'):
            messages.append({'role': 'system', 'content': text(body['instructions'])})
        for item in canonical_tool_history(body.get('input', [])):
            kind = item.get('type', 'message')
            if kind == 'message':
                content = text(item.get('content'))
                if content:
                    messages.append({'role': 'system' if item['role'] == 'developer' else item['role'], 'content': content})
            elif kind == 'function_call':
                tc = {'id': item['call_id'], 'type': 'function', 'function':
                      {'name': item['name'], 'arguments': item['arguments']}}
                if messages and messages[-1].get('tool_calls'):
                    messages[-1]['tool_calls'].append(tc)
                else:
                    messages.append({'role': 'assistant', 'content': None, 'tool_calls': [tc]})
            elif kind == 'function_call_output':
                output = item['output']
                messages.append({'role': 'tool', 'tool_call_id': item['call_id'],
                    'content': output if isinstance(output, str) else json.dumps(output)})
            else:
                raise ValueError('Unsupported Responses item: ' + str(kind))
        for tool in body.get('tools', []):
            if tool.get('type') != 'function':
                raise ValueError('Only local function tools permitted')
            tools.append({'type': 'function', 'function': {k: tool[k] for k in ('name', 'description', 'parameters') if k in tool}})
    elif path == '/v1/messages':
        if body.get('system'):
            messages.append({'role': 'system', 'content': text(body['system'])})
        for msg in body['messages']:
            blocks = msg['content']
            if isinstance(blocks, str):
                messages.append({'role': msg['role'], 'content': blocks})
                continue
            pending = []
            calls = []
            for block in blocks:
                kind = block['type']
                if kind == 'text':
                    pending.append(block['text'])
                elif kind == 'tool_use':
                    calls.append({'id': block['id'], 'type': 'function', 'function':
                        {'name': block['name'], 'arguments': json.dumps(block['input'])}})
                elif kind == 'tool_result':
                    if pending:
                        messages.append({'role': msg['role'], 'content': '\n'.join(pending)})
                        pending = []
                    messages.append({'role': 'tool', 'tool_call_id': block['tool_use_id'], 'content': text(block.get('content')) or '[empty tool result]'})
                else:
                    raise ValueError('Unsupported Anthropic block: ' + kind)
            if pending or calls:
                row = {'role': msg['role'], 'content': '\n'.join(pending) or None}
                if calls:
                    row['tool_calls'] = calls
                messages.append(row)
        for tool in body.get('tools', []):
            if tool.get('type', 'custom') != 'custom':
                raise ValueError('Server tools unsupported')
            tools.append({'type': 'function', 'function': {'name': tool['name'],
                'description': tool.get('description', ''), 'parameters': tool['input_schema']}})
    elif path == '/v1/chat/completions':
        messages = body['messages']
        tools = body.get('tools', [])
        if any(t.get('type') != 'function' for t in tools):
            raise ValueError('Only local function tools permitted')
    else:
        raise ValueError('Endpoint not allowed')
    messages = [dict(m) for m in messages]
    for msg in messages:
        if msg['role'] not in ('system', 'user', 'assistant', 'tool'):
            raise ValueError('Unsupported message role')
        if not msg.get('tool_calls'):
            msg['content'] = text(msg.get('content')) or '[empty observation]'
    requested = body.get('max_output_tokens', body.get('max_completion_tokens', body.get('max_tokens')))
    if requested is not None and (type(requested) is not int or requested <= 0):
        raise ValueError('Invalid output budget')
    if cap is not None and (type(cap) is not int or cap <= 0):
        raise ValueError('Invalid legacy output budget')
    effective = requested if cap is None else (min(requested, cap) if requested is not None else cap)
    result = {'model': model, 'messages': messages, 'stream': False}
    if effective is not None:
        key = 'max_completion_tokens' if path == '/v1/chat/completions' and 'max_completion_tokens' in body else 'max_tokens'
        result[key] = effective
    if tools:
        result['tools'] = tools
    choice = body.get('tool_choice')
    if choice in ('none', 'auto', 'required'):
        result['tool_choice'] = choice
    elif isinstance(choice, dict) and choice.get('type') == 'tool':
        result['tool_choice'] = {'type': 'function', 'function': {'name': choice['name']}}
    return result


def event(kind, data):
    return ('event: ' + kind + '\ndata: ' + json.dumps(data, ensure_ascii=False) + '\n\n').encode()


def response(path, body, streamed):
    from ..provider_outcome import response_problem, ProviderResponseError
    problem = response_problem(body)
    if problem:
        choice = (body.get("choices") or [{}])[0] if isinstance(body, dict) else {}
        raise ProviderResponseError(problem, choice.get("finish_reason") if isinstance(choice, dict) else None)
    choice, = body['choices']
    msg, reason = choice['message'], choice['finish_reason']
    calls = msg.get('tool_calls') or []
    content = msg.get('content') or ''
    if not content and not calls:
        raise ValueError('Provider returned neither text nor tool calls')
    usage = body.get('usage') or {}
    identifier = body['id']
    if path == '/v1/responses':
        output = []
        if content:
            output.append({'type': 'message', 'id': 'msg_' + identifier, 'role': 'assistant',
                'status': 'completed', 'content': [{'type': 'output_text', 'text': content, 'annotations': []}]})
        for tc in calls:
            output.append({'type': 'function_call', 'id': 'fc_' + tc['id'], 'call_id': tc['id'],
                'name': tc['function']['name'], 'arguments': tc['function']['arguments'], 'status': 'completed'})
        value = {'object': 'response', 'id': 'resp_' + identifier, 'model': body.get('model'),
            'status': 'completed' if reason in ('stop', 'tool_calls') else 'incomplete', 'output': output,
            'error': None, 'incomplete_details': None if reason in ('stop', 'tool_calls') else {'reason': 'max_output_tokens' if reason == 'length' else reason},
            'usage': {'input_tokens': usage.get('prompt_tokens', 0), 'output_tokens': usage.get('completion_tokens', 0), 'total_tokens': usage.get('total_tokens', 0)}}
        return ('text/event-stream', terminal_response_events(value)) if streamed else ('application/json', json.dumps(value).encode())
    if path == '/v1/messages':
        blocks = ([{'type': 'text', 'text': content}] if content else []) + [
            {'type': 'tool_use', 'id': tc['id'], 'name': tc['function']['name'], 'input': json.loads(tc['function']['arguments'])} for tc in calls]
        stop = 'tool_use' if calls else ('max_tokens' if reason == 'length' else 'end_turn')
        use = {'input_tokens': usage.get('prompt_tokens', 0), 'output_tokens': usage.get('completion_tokens', 0)}
        value = {'id': 'msg_' + identifier, 'type': 'message', 'role': 'assistant', 'model': body.get('model'),
                 'content': blocks, 'stop_reason': stop, 'stop_sequence': None, 'usage': use}
        if not streamed:
            return 'application/json', json.dumps(value).encode()
        data = event('message_start', {'type': 'message_start', 'message': {**value, 'content': [], 'stop_reason': None, 'usage': {**use, 'output_tokens': 0}}})
        for index, block in enumerate(blocks):
            start = {**block, **({'text': ''} if block['type'] == 'text' else {'input': {}})}
            delta = {'type': 'text_delta', 'text': block['text']} if block['type'] == 'text' else {'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])}
            data += event('content_block_start', {'type': 'content_block_start', 'index': index, 'content_block': start})
            data += event('content_block_delta', {'type': 'content_block_delta', 'index': index, 'delta': delta})
            data += event('content_block_stop', {'type': 'content_block_stop', 'index': index})
        data += event('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': stop, 'stop_sequence': None}, 'usage': {'output_tokens': use['output_tokens']}})
        return 'text/event-stream', data + event('message_stop', {'type': 'message_stop'})
    if not streamed:
        return 'application/json', json.dumps(body).encode()
    def chunk(delta, finish=None, usage=None):
        value = {'id': identifier, 'object': 'chat.completion.chunk', 'created': body.get('created', 0),
                 'model': body.get('model'), 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
        if usage is not None:
            value['usage'] = usage
        return ('data: ' + json.dumps(value) + '\n\n').encode()
    # Chat -> Chat must preserve provider reasoning and extra assistant fields.
    # In particular, Kimi needs reasoning_content in the next tool-result turn.
    delta = {**msg, 'role': 'assistant', 'content': content}
    if calls:
        delta['tool_calls'] = [dict(tc, index=i) for i, tc in enumerate(calls)]
    return 'text/event-stream', chunk(delta) + chunk({}, reason, usage) + b'data: [DONE]\n\n'
