import copy
import csv
import json
from pathlib import Path
import socket
import subprocess

import pytest

from expert_review import bind, collect, digest, export, receipt, thinking_text
from fable_expert_notes import NOTES

PROJECT = Path(__file__).resolve().parents[1]


def test_thinking_is_not_duplicated_or_invented():
    assert thinking_text({}) == ''
    assert thinking_text({'provider_specific_fields': {'thinking_blocks': [{'thinking': 'fragment'}]},
                          'thinking_blocks': [{'thinking': 'fragment'}], 'reasoning_content': 'fragment'}) == 'fragment'
    assert thinking_text({'reasoning_content': 'fallback'}) == 'fallback'


def test_receipt_tampering_is_rejected(tmp_path):
    path = tmp_path / 'receipt.json'
    path.write_text(json.dumps({'payload': {'answer': 1}, 'hash': digest({'answer': 2})}))
    with pytest.raises(ValueError, match='证据校验'):
        receipt(path)


@pytest.fixture
def viscosity():
    return collect(PROJECT / 'runs/fable-edge-live-002/trials/s-203', 's-203')


def test_planned_read_is_not_counted_as_executed(viscosity):
    result = bind(viscosity, NOTES['s-203'])
    last = result['calls'][-1]
    assert last['finish_reason'] == 'length'
    assert 'docs.py read d-7ee4' in last['tools'][0]['arguments']['cmd']
    assert not last['tools'][0]['execution_observed']
    assert last['tools'][1]['arguments'] == {}
    assert last['expert_review']['training_eligibility'] == 'hold'
    assert last['expert_review']['groundtruth'] is None


def test_exact_search_mapping_and_agent_clipping(viscosity):
    queries = viscosity['queries']
    assert len(queries) == 7
    assert queries[1]['query'] == 'energyTransport'
    assert len(queries[1]['model_visible_commands']) == 1
    assert all(q['client_output_observed'] for q in queries)
    assert [q['agent_clipped_output'] for q in queries] == [False] * 5 + [True, True]
    body = queries[4]['response']
    if isinstance(body, str):
        body = json.loads(body)
    assert body['results'][0]['id'] == 'd-7ee4fb189fc30d26e84e'


@pytest.mark.parametrize('mode', ['missing_call', 'wrong_anchor', 'wrong_query', 'truncated_but_executed'])
def test_annotation_drift_is_rejected(viscosity, mode):
    notes = copy.deepcopy(NOTES['s-203'])
    if mode == 'missing_call':
        notes['calls'].pop()
    if mode == 'wrong_anchor':
        notes['calls'][0]['anchor'] = 'invented impossible statement'
    if mode == 'wrong_query':
        notes['queries'][0]['keyword'] = 'wrong query'
    if mode == 'truncated_but_executed':
        viscosity['calls'][-1]['tools'][0]['execution_observed'] = True
    with pytest.raises(ValueError):
        bind(viscosity, notes)


def test_report_export_is_read_only_complete_and_repeatable(tmp_path, monkeypatch):
    def no_external(*args, **kwargs):
        raise AssertionError('Review must not call processes/network')
    monkeypatch.setattr(socket, 'socket', no_external)
    monkeypatch.setattr(subprocess, 'Popen', no_external)
    results = [export(PROJECT, tmp_path / str(i)) for i in range(2)]
    assert results[0]['review_id'] == results[1]['review_id']
    assert results[0]['calls'] == 42 and results[0]['queries'] == 7
    evidence = json.loads((tmp_path / '0/evidence.json').read_text())
    records = [v for case in evidence['cases'] for v in case['calls'] + case['queries']]
    assert len({v['id'] for v in records}) == 49
    assert all(v['expert_review']['status'] == 'unreviewed' for v in records)
    assert all(v['expert_review']['training_eligibility'] == 'hold' for v in records)
    for case in evidence['cases']:
        assert all(c['output_limit_parameters'] == {} for c in case['calls'])
    with (tmp_path / '0/专家意见.csv').open(encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 49 and all(row['审阅状态'] == '未审阅' for row in rows)
    assert not any(row['知识依据或标准答案'] for row in rows)
    before = (tmp_path / '0/专家意见.csv').read_bytes()
    with pytest.raises(FileExistsError):
        export(PROJECT, tmp_path / '0')
    assert (tmp_path / '0/专家意见.csv').read_bytes() == before
    text = (tmp_path / '0/s-203.md').read_text()
    assert '选择' in text and '未执行' in text and 'head -c 3000' in text
