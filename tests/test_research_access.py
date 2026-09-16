import json
from pathlib import Path

import pytest

from agentcfd_bench.harnesses import research
from agentcfd_bench.harnesses.codex import protocol_for
from agentcfd_bench.harnesses._transport.adapters.native_responses import local_request_tools
from agentcfd_bench.harnesses._transport.live_transcript import StreamCapture
from agentcfd_bench.records.transcript import Transcript
from agentcfd_bench.tasks.experiment import load
from agentcfd_bench.tasks.loader import Task

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('task_id', ['s-203', 's-204'])
def test_online_prompt_and_matched_experiment(task_id):
    online, _ = load(ROOT / f'experiments/dense-reconstruction-astra-web-120-{task_id.replace("-", "")}.yaml')
    offline, _ = load(ROOT / 'experiments/dense-reconstruction-astra-120.yaml')
    for key in ('model', 'harness', 'task_root', 'docs', 'budget', 'completion', 'execution'):
        assert online[key] == offline[key]
    assert online['tasks'] == [task_id]
    task = Task.load(Path(online['task_root']) / task_id)
    prompt = protocol_for(task, online)
    assert 'enabled in LIVE mode' in prompt
    assert 'exact search query' in prompt and 'what you learned' in prompt
    assert 'Public internet and other tasks are unavailable' not in prompt
    assert 'no direct internet route' in prompt
    assert 'intentionally public' in prompt
    assert 'Public internet and other tasks are unavailable' in protocol_for(task, offline)
    assert research.facts(online)['shell_and_solver_network'] == 'disabled'


@pytest.mark.parametrize('kind', ['web_search', 'web_search_preview'])
def test_web_tools_are_only_admitted_under_explicit_policy(kind):
    for body in ({'tools':[{'type':kind}]},
                 {'input':[{'type':'additional_tools','tools':[{'type':kind}]}]},
                 {'tools':[{'type':'namespace','name':'web','tools':[{'type':kind}]}]}):
        assert not local_request_tools(body)
        assert local_request_tools(body, allow_web_search=True)


@pytest.mark.parametrize('kind', ['mcp', 'file_search', 'computer_use_preview', 'code_interpreter'])
def test_web_mode_does_not_enable_other_hosted_tools(kind):
    assert not local_request_tools({'tools':[{'type':kind}]}, allow_web_search=True)
    assert not local_request_tools({'input':[{'type':'additional_tools','tools':[{'type':kind}]}]}, allow_web_search=True)


@pytest.mark.parametrize('harness', [
    {'name':'codex','backend':'custom-api'},
    {'name':'kimi-code','backend':'custom-api'},
])
def test_unsupported_bridge_cannot_claim_online_capability(harness):
    assert not research.live({'network':'disabled','harness':harness})
    with pytest.raises(ValueError, match='native Responses'):
        research.live({'network':research.LIVE,'harness':harness})


def test_query_capture_is_live_deduplicated_and_not_invented(tmp_path):
    stream = StreamCapture(Transcript(tmp_path))
    item = {'type':'web_search_call','id':'ws-1','status':'completed',
            'action':{'type':'open_page','url':'https://doc.openfoam.com/2306/'}}
    events = [{'type':'response.output_item.done','item':item},
              {'type':'response.completed','response':{'output':[item]}}]
    for e in events:
        wire=('data: '+json.dumps(e)+'\n\n').encode()
        stream.feed(wire[:19]); stream.feed(wire[19:])
    entries = [json.loads(line) for line in (tmp_path/'transcript.jsonl').read_text().splitlines()]
    rows = [e for e in entries if e['kind']=='web_retrieval']
    assert len(rows)==1 and rows[0]['payload']['provider_item']==item
    assert 'missing page text is not reconstructed' in rows[0]['payload']['capture_scope']
    assert '联网查询／阅读' in (tmp_path/'transcript.md').read_text()
