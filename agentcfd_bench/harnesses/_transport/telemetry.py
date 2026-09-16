"""Usage is an observation, never a budget. Read only durable provider receipts.

Missing usage/cost is unknown, not zero. Reasoning/cached tokens are subsets of
output/input respectively; do not add them again to total_tokens. No price guesses.
"""
import json
import math
from pathlib import Path

from .journal import read_receipt

FIELDS = ('input_tokens', 'output_tokens', 'total_tokens', 'reasoning_tokens', 'cached_input_tokens')


def empty():
    return {'requests': 0, 'known_responses': 0, 'output_truncations': 0,
            **dict.fromkeys(FIELDS), 'coverage': dict.fromkeys(FIELDS, 0),
            'reported_cost_by_currency': {}, 'cost_covered_requests': 0, 'documentation': None}


def merge(left, right):
    result = empty()
    for item in (left, right):
        if not item:
            continue
        for key in ('requests', 'known_responses', 'output_truncations', 'cost_covered_requests'):
            result[key] += item.get(key, 0)
        for key in FIELDS:
            if item.get(key) is not None:
                result[key] = (result[key] or 0) + item[key]
            result['coverage'][key] += item.get('coverage', {}).get(key, 0)
        for currency, cost in item.get('reported_cost_by_currency', {}).items():
            result['reported_cost_by_currency'][currency] = result['reported_cost_by_currency'].get(currency, 0) + cost
        from .documentation_statistics import merge_doc_usage as merge_usage
        result['documentation'] = merge_usage(result['documentation'], item.get('documentation'))
    return result


def terminal_body(raw):
    """Take ONE terminal usage from JSON or SSE, not every streaming update."""
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except ValueError:
        pass
    terminal = {}
    completed_items = {}
    for line in raw.splitlines():
        if not line.startswith('data:'):
            continue
        try:
            value = json.loads(line[5:].strip())
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        if value.get('type') == 'response.created':
            completed_items = {}
        if value.get('type') == 'response.output_item.done':
            index, item = value.get('output_index'), value.get('item')
            if type(index) is int and index >= 0 and isinstance(item, dict):
                completed_items[index] = item
        if value.get('type') in ('response.completed', 'response.incomplete', 'response.failed'):
            terminal = dict(value.get('response') or {})
            # Native Codex may send completed items only in item.done events,
            # leaving response.completed.output empty. Reconstruct the observed
            # view, never the stored/on-wire response; deltas alone are not items.
            if not terminal.get('output') and completed_items:
                terminal['output'] = [completed_items[k] for k in sorted(completed_items)]
        elif value.get('usage') is not None:
            terminal = value
    return terminal if isinstance(terminal, dict) else {}


def measure(body):
    result = empty()
    usage = body.get('usage') or {}
    if not isinstance(usage, dict):
        usage = {}
    output_details = usage.get('output_tokens_details') or usage.get('completion_tokens_details') or {}
    input_details = usage.get('input_tokens_details') or usage.get('prompt_tokens_details') or {}
    output_details = output_details if isinstance(output_details, dict) else {}
    input_details = input_details if isinstance(input_details, dict) else {}
    values = {'input_tokens': usage.get('input_tokens', usage.get('prompt_tokens')),
              'output_tokens': usage.get('output_tokens', usage.get('completion_tokens')),
              'total_tokens': usage.get('total_tokens'),
              'reasoning_tokens': output_details.get('reasoning_tokens'),
              'cached_input_tokens': input_details.get('cached_tokens')}
    for key, value in values.items():
        if type(value) is int and value >= 0:
            result[key], result['coverage'][key] = value, 1
    choices = body.get('choices') or []
    details = body.get('incomplete_details') or {}
    result['output_truncations'] = int(any(isinstance(c, dict) and c.get('finish_reason') == 'length' for c in choices)
        or (isinstance(details, dict) and details.get('reason') in ('max_output_tokens', 'length')))
    # Accept explicitly identified, provider-reported monetary observations only.
    cost = body.get('cost') or usage.get('cost')
    if isinstance(cost, dict):
        amount, currency = cost.get('amount'), cost.get('currency')
        if type(amount) in (int, float) and math.isfinite(amount) and amount >= 0 and isinstance(currency, str) and currency:
            result['reported_cost_by_currency'][currency] = amount
            result['cost_covered_requests'] = 1
    return result


def collect(directory):
    result = empty()
    for path in sorted(Path(directory).glob('call-*')):
        if not path.is_dir():
            continue
        receipt = read_receipt(path/'complete.json')
        row = empty()
        row['requests'] = 1
        if receipt is not None:
            row['known_responses'] = 1
            raw = path/'response.raw'
            if raw.is_file():
                row = merge(row, measure(terminal_body(raw.read_text(errors='replace'))))
        result = merge(result, row)
    from .documentation_statistics import usage
    result['documentation'] = usage(Path(directory)/'documentation')
    return result
