"""Offline, immutable expert-review exports; no model, solver or scheduler imports.

Human-readable interpretations are editorial annotations, never new ground truth.
Provider thinking is treated as an incomplete returned fragment, not certified CoT.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def receipt(path):
    value=json.loads(Path(path).read_text())
    if digest(value['payload']) != value['hash']:
        raise ValueError(f'证据校验失败：{path}')
    return value['payload']


def source(path):
    path=Path(path).resolve()
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def thinking_text(message):
    # Gateways may duplicate the same text in three fields. Never count it thrice.
    blocks=message.get('provider_specific_fields',{}).get('thinking_blocks') or message.get('thinking_blocks') or []
    texts=[b['thinking'] for b in blocks if isinstance(b,dict) and isinstance(b.get('thinking'),str)]
    if not texts and isinstance(message.get('reasoning_content'),str):
        texts=[message['reasoning_content']]
    return '\n'.join(dict.fromkeys(texts)).strip()


def collect(root,task_id):
    root=Path(root).resolve()
    score=json.loads((root/'scoreboard.json').read_text())
    submissions=sorted((root/'agent').glob('*/submission-*'),key=lambda p:int(p.name.split('-')[-1]))
    calls=[]; queries=[]; warnings=[]
    for submission in submissions:
        events_path=submission/'events.jsonl'
        events=[json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
        completed=[e['item'] for e in events if e.get('type')=='item.completed']
        warnings.extend({'message':e.get('message'),'source':source(events_path)} for e in completed if e.get('type')=='error')
        call_dirs=sorted((submission/'api').glob('call-*'))
        outputs={}
        for folder in call_dirs:
            wire=receipt(folder/'wire_request.json')
            for m in wire['body'].get('messages',[]):
                if m.get('role')=='tool' and m.get('tool_call_id'):
                    outputs[m['tool_call_id']]=m.get('content','')
        for folder in call_dirs:
            raw=json.loads((folder/'response.raw').read_text())
            choice=raw['choices'][0]; message=choice['message']
            wire=receipt(folder/'wire_request.json')['body']
            dispatch=receipt(folder/'dispatch.json')
            tools=[]
            for tool in message.get('tool_calls') or []:
                args=json.loads(tool['function']['arguments'])
                output=outputs.get(tool['id'])
                tools.append({'name':tool['function']['name'],'arguments':args,
                    'observation':output,'execution_observed':output is not None})
            calls.append({'id':f'{task_id}-C{len(calls)+1:02d}',
                'submission':submission.name,'local_call':folder.name,
                'time_utc':datetime.fromtimestamp(dispatch['time'],timezone.utc).strftime('%H:%M:%S'),
                'finish_reason':choice.get('finish_reason'),'thinking':thinking_text(message),
                'public_text':message.get('content') or '', 'tools':tools,
                'output_tokens':raw.get('usage',{}).get('completion_tokens'),
                'output_limit_parameters':{k:wire[k] for k in ('max_tokens','max_completion_tokens','max_output_tokens') if k in wire},
                'evidence':[source(folder/'response.raw'),source(folder/'wire_request.json'),source(events_path)]})
        for folder in sorted((submission/'api/documentation').glob('query-*')):
            request=receipt(folder/'request.json'); response=receipt(folder/'response.json')
            query=request['body'].get('query','')
            matches=[e for e in completed if e.get('type')=='command_execution' and ('search "'+query+'"') in e.get('command','')]
            queries.append({'id':f'{task_id}-Q{len(queries)+1:02d}','query':query,
                'request':request['body'],'response':response['body'],
                'model_visible_commands':[e['command'] for e in matches],
                'agent_clipped_output':any('head -c 3000' in e['command'] for e in matches),
                'client_output_observed':bool(matches),'evidence':[source(folder/'request.json'),source(folder/'response.json'),source(events_path)]})
    if len(calls)!=score['model_calls']:
        raise ValueError(f'{task_id}: request ledger and scoreboard disagree')
    return {'id':task_id,'root':str(root),'score':score,'calls':calls,'queries':queries,'client_warnings':warnings}


def bind(case,notes):
    """Refuse silently attaching old prose to new calls or unexecuted actions."""
    if len(case['calls'])!=len(notes['calls']): raise ValueError('逐次注释覆盖不完整')
    for call,note in zip(case['calls'],notes['calls']):
        if note['anchor'] not in (call['thinking']+'\n'+call['public_text']+'\n'+json.dumps(call['tools'],ensure_ascii=False)):
            raise ValueError(f"注释证据锚不匹配：{call['id']}")
        if call['finish_reason']=='length' and any(t['execution_observed'] for t in call['tools']):
            raise ValueError('截断响应含已执行动作，需要独立人工审阅，不能按未执行模板导出')
        call['annotation']=note
        call['thinking_visibility']='returned_fragment' if call['thinking'] else 'not_returned'
        call['expert_review']={'status':'unreviewed','cause':None,'correction':None,
            'training_eligibility':'hold','groundtruth':None}
    if len(case['queries'])!=len(notes.get('queries',[])):
        raise ValueError('检索注释覆盖不完整')
    for query,note in zip(case['queries'],notes.get('queries',[])):
        if query['query']!=note['keyword']: raise ValueError('检索关键词错配')
        query['annotation']=note
        query['expert_review']={'status':'unreviewed','cause':None,'correction':None,
            'training_eligibility':'hold','groundtruth':None}
    case['editorial']= {k:v for k,v in notes.items() if k not in ('calls','queries')}
    return case


def link(label,path):
    return f'[{label}](<{path}>)'


def cell(value):
    return str(value).replace('|','\\|').replace('\n',' ')


def evidence_links(items):
    return ' · '.join(link('证据'+str(i+1),v['path']) for i,v in enumerate(items))


def render_case(case):
    e=case['editorial']; s=case['score']
    lines=[f"# {case['id']}｜{e['title']}",'',f"一句话任务：{e['task']}",'',
        f"**本题结论：{e['outcome']}**",'',f"优先审阅：{e['priority']}",'',
        f"真实计数：{s['model_calls']} 次模型调用；{s['run_submissions']} 次 OpenFOAM 提交；{s['native_runs_completed']} 次完整运行。",'',
        '阅读规则：下文“思考”是上游实际返回片段的中文摘要，不是完整内部思维链。',
        '“决策”分为已执行或仅计划；“初步归因”由报告作者提出，须专家确认。',
        '每个 C 编号对应一次 API 请求，不是一次 OpenFOAM 提交；时间均为 UTC。','',
        '## 先看会改变结论的事实','',e['review'],'','## 逐次过程卡','']
    for c in case['calls']:
        n=c['annotation']
        lines += [f"### {c['id']}｜{n['title']}（{c['time_utc']}）",'',
            f"- 当时看到：{n['observation']}",
            f"- Agent 思考：{n['thinking'] if c['thinking'] else '本次没有返回独立思考片段；以下决策仅按公开文字和动作描述。'}",
            f"- 决策／拟采取措施：{n['decision']}",
            f"- 实际 action：{n['action']}",
            f"- 实际结果／下一步反馈：{n['result']}",
            f"- 初步归因：{n['issue']}",
            f"- 请专家判断：{n['question']}",'']
        if c['finish_reason']=='length':
            lines += [f"接口事实：返回 `length`，输出 {c['output_tokens']} token；适配器拒绝整份响应，未执行其中工具。请求中的输出上限参数：{c['output_limit_parameters'] or '无'}。",'']
        for i,t in enumerate(c['tools'],1):
            if not t['execution_observed']:
                proposed=t['arguments'].get('cmd') or '空参数，没有可执行命令'
                lines += [f'未执行的拟调用 {i}：`{proposed}`。没有后续工具回执，不能算成已执行操作。','']
        lines += [f"证据定位：{c['submission']} / {c['local_call']}；{evidence_links(c['evidence'])}。",
            '审阅意见：□同意归因 □改归因 □证据不足；建议的正确操作：____；训练用途：____。','']
    lines += ['## 原生提交与验收（不是模型自报）','',
        '| 提交 | 真实结果 | 对 Agent 的后续影响 |','|---|---|---|']
    for row in e.get('native',[]): lines.append('| '+' | '.join(cell(v) for v in row)+' |')
    if not e.get('native'): lines += ['| 无 | 没有提交到 OpenFOAM，无法评价配置或物理结果 | 不应记成物理失败 |']
    if case['queries']:
        lines += ['','## 检索卡：关键词 → 返回 → 采纳 → 下一步','',
            '返回内容由检索凭据核实；“重要／已采纳”只能来自 Agent 的明确表述。',
            '没有明确选择的条目统一标为未记录，绝不把回忆或猜测伪装成检索结论。','']
        for q in case['queries']:
            n=q['annotation']; body=q['response']
            if isinstance(body,str): body=json.loads(body)
            lines += [f"### {q['id']}｜{n['goal']}",'',
                f"- 怎么查：固定只读 OpenFOAM 文档检索；原样关键词 **`{q['query']}`**；offset={q['request'].get('offset')}，limit={q['request'].get('limit')}。",
                f"- 服务返回：匹配总数 {body.get('total','未知')}；本页 {len(body.get('results',[]))} 条。",
                f"- 返回知识（报告作者概括，不代表 Agent 采纳）：{n['returned']}",
                f"- Agent 自己认为重要的知识：{n['adopted']}",
                f"- 对下一步的影响：{n['effect']}",
                f"- 管线／操作问题：{n['issue']}",
                f"- 完整阅读情况：未完成全文读取（Q05 的后续读取请求被截断响应整体拒绝）；{'Agent 主动用 head -c 3000 裁掉后半段，只能确认看到部分返回。' if q['agent_clipped_output'] else '工具回执中有本次搜索输出。'}",'']
            lines += ['实际返回标题：'+ '；'.join(r['title'] for r in body.get('results',[]))+'。','',
                '证据：'+evidence_links(q['evidence'])+'。',
                '审阅意见：应采纳的条目／知识：____；应换的关键词或资料：____；错误归因：____。','']
    else: lines += ['','## 查资料情况','','本题轨迹没有文档搜索／阅读记录。识别出 tutorial 名称属于模型识别或回忆，不是查过资料的证据。','']
    lines += ['## 接口与客户端共同风险','',
        f"本题 {len(case['client_warnings'])} 个客户端会话记录了模型元数据 fallback 警告。",
        '这是本地 Codex 对网关模型名缺少内置配置的提示；不能仅凭它认定已降智，也不能忽略兼容风险。',
        '原生错误、数值验收失败、客户端警告、上游截断是不同事件，不能合并计数。','']
    return '\n'.join(lines)


def export(project,output):
    from fable_expert_notes import NOTES, OVERVIEW
    project=Path(project).resolve(); output=Path(output).resolve()
    if output.exists(): raise FileExistsError('审阅包不可覆盖，请使用新目录，保护专家已填意见')
    cases=[]
    for task_id,notes in NOTES.items():
        root=project/('runs/fable-edge-live-001/s-105' if task_id=='s-105' else 'runs/fable-edge-live-002/trials/'+task_id)
        cases.append(bind(collect(root,task_id),notes))
    # Validate everything before creating output. This command reads no credentials.
    output.mkdir(parents=True)
    manifest={'version':'expert-review-v1','interpretation_status':'assistant_draft_not_expert_groundtruth',
        'cases':cases,'generator':source(__file__), 'annotations':source(Path(__file__).with_name('fable_expert_notes.py'))}
    manifest['review_id']=digest(manifest)
    (output/'evidence.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    for case in cases: (output/(case['id']+'.md')).write_text(render_case(case))
    feedback=[]
    for c in cases:
        for r in c['calls']+c['queries']:
            feedback.append({'审阅包':manifest['review_id'],'定位编号':r['id'],'任务':c['editorial']['title'],
                '审阅状态':'未审阅','专家姓名':'','是否同意初步归因':'','主因':'','次因':'',
                '错误知识或步骤':'','建议的正确操作':'','知识依据或标准答案':'',
                '训练用途':'待审，不自动入库','备注':''})
    with (output/'专家意见.csv').open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(feedback[0])); writer.writeheader(); writer.writerows(feedback)
    (output/'专家意见.json').write_text(json.dumps(feedback,ensure_ascii=False,indent=2)+'\n')
    rows=['# Fable 五题｜专家审阅入口','',OVERVIEW,'',
        '| 题目 | 当前结论 | 优先看哪一步 |','|---|---|---|']
    for c in cases:
        e=c['editorial']; rows.append('| '+link(e['title'],output/(c['id']+'.md'))+' | '+e['outcome']+' | '+e['priority']+' |')
    rows += ['','管线／接口排查请看 '+link('中文归因表',project/'docs/EXPERT_PIPELINE_REVIEW.md')+'：已证实故障、保守适配策略和基准定义风险分开。',
        '','## 怎么给意见','',
        '直接回复“s-204-C11：我认为……；应当……；是否可用于训练……”即可定位。',
        '也可用表格软件填写 '+link('专家意见.csv',output/'专家意见.csv')+'，一行对应一步／一次检索。',
        '主因建议：物理理解／数值方法／配置语法／检索策略／资料缺口／接口／管线／基准定义／无错／证据不足。',
        '原始评分不随意见自动改变；专家确认、标准答案核实和数据版本登记后，才决定是否入训练集。','',
        '## 完整性与边界','',
        f"覆盖 {sum(len(c['calls']) for c in cases)} 次模型请求、{sum(len(c['queries']) for c in cases)} 次检索、全部 5 次原生提交。",
        '每步都有原始凭据路径与 SHA256；中文解释是报告作者的草稿，不是 Agent 逐字原话或专家结论。',
        '上游返回的 thinking 只是可见片段，可能不完整；计划写文件不等于工具执行，更不等于已经提交求解。',
        '本次只重组历史记录，没有请求模型、重跑 OpenFOAM、改旧提示词、改评分或自动制造训练标签。','']
    (output/'index.md').write_text('\n'.join(rows))
    return {'review_id':manifest['review_id'],'cases':len(cases),'calls':sum(len(c['calls']) for c in cases),
        'queries':sum(len(c['queries']) for c in cases),'index':str(output/'index.md')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True); p.add_argument('--output',required=True)
    args=p.parse_args(); print(json.dumps(export(args.project,args.output),ensure_ascii=False))
