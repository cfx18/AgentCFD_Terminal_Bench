"""Read-only five-task study summary. Never imports private task evaluators."""
import argparse
import json
from pathlib import Path
import time

from agentcfd_bench.journal import read_receipt
from agentcfd_bench.reporting import atomic,report

NAMES={'s-105':'压力驱动分支流＋标量源项','s-202':'多区域传热＋接触热阻',
       's-203':'温度依赖黏度＋能量方程','s-204':'三维腔体自然对流','s-205':'可压缩激波管'}


def pending_status(campaign, task_id, previous):
    """Display a declared replacement control gate without erasing its predecessor."""
    root=Path(campaign)/'deferred'
    spec=read_receipt(root/'spec.json')
    if not spec or spec.get('task',{}).get('id')!=task_id:
        return previous
    finished=read_receipt(root/'finished.json')
    return {'status':(finished['status'] if finished else '修订对照待验收／尚未调用模型'),
            'previous_attempt':previous,'deferred_spec':spec,'deferred_finished':finished}


def summarize(project, campaign):
    project,campaign=Path(project).resolve(),Path(campaign).resolve()
    rows=[]
    for task_id,title in NAMES.items():
        root=(project/'runs/fable-edge-live-001/s-105' if task_id=='s-105' else campaign/'trials'/task_id)
        status=read_receipt(campaign/'campaign'/(task_id+'.json')) if task_id!='s-105' else None
        if (root/'state.sqlite').is_file():
            data=report(root,write=True)
            rows.append({'id':task_id,'title':title,'root':str(root),'score':data,'campaign_status':status})
        else:
            rows.append({'id':task_id,'title':title,'root':str(root),'score':None,
                         'campaign_status':pending_status(campaign,task_id,status)})
    values=[r['score'] for r in rows if r['score']]
    data={'model':'AWS-Claude-Fable-5','registered_tasks':5,
          'completed':sum(v['lifecycle']=='completed' for v in values),
          'passed':sum(v['verdict']=='pass' for v in values),'rows':rows,
          'controller_finished':(campaign/'campaign/finished.json').is_file() and (
              not (campaign/'continuations/spec.json').exists() or (campaign/'continuations/finished.json').is_file()) and (
              not (campaign/'deferred/spec.json').exists() or (campaign/'deferred/finished.json').is_file())}
    data['rates_are_final']=data['completed']==5
    lines=['# Fable 5：五题物理建模实验','',
       '实际客户端：Codex CLI；实际请求模型：AWS-Claude-Fable-5。',
       '从空匿名目录建模，可查固定只读 OpenFOAM 文档，不开放公网。',
       '本轮是固定网格的数值复现与报告核对；独立热流／总能量守恒专项验收未完成。',
       '首题沿用已完成的原试验；其余四题不重复首题，也不更换为简单题。','',
       '| 题目 | 状态 / 验收 | 调用数 | 原生提交 / 完整运行 | 启动 / 数值 / 输入失败 | 报告失真 / 物理检查失败 | 基础设施事件 |',
       '|---|---|---:|---:|---:|---:|---:|']
    for row in rows:
        v=row['score']; title=row['id']+' '+row['title']
        if v:
            failed=v['failures_by_stage']
            lines.append(f"| {title} | {v['lifecycle']} / {v['verdict']} | {v['model_calls']} | "
               f"{v['run_submissions']} / {v['native_runs_completed']} | {failed.get('startup',0)} / "
               f"{failed.get('numerical',0)} / {failed.get('input_validation',0)} | "
               f"{v['report_faithfulness_failures']} / {v['physical_acceptance_failures']} | {v['infrastructure_events']} |")
        else:
            status=(row['campaign_status'] or {}).get('status','等待原生资格检查／模型启动')
            lines.append(f'| {title} | {status} | — | — | — | — | — |')
    lines+=['',f"已完成 {data['completed']} / 5；通过 {data['passed']} 题。"+
            ('全部完成。' if data['rates_are_final'] else '尚不能作为五题最终准确率。'),'',
            '物理检查失败不是自动认定的物理理解错误：需要结合具体配置差异、数值误差及轨迹做人工归因。',
            '工作流／格式失败、参考或运行环境故障、API 异常均须单列，不混算成物理能力失败。','',
            '## 单题完整记录','']
    for row in rows:
        root=Path(row['root'])
        lines.append('- '+row['id']+': ['+row['title']+']('+str(root/'scoreboard.md')+')；轨迹目录 `'+str(root/'agent')+'`。')
    lines+=['','原始单题报告包含每一次原生提交和验收结论；请求与响应、工具操作和文档访问记录保留在轨迹目录。','']
    return data,'\n'.join(lines)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True); parser.add_argument('--campaign',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--watch',action='store_true')
    args=parser.parse_args(); output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
    previous=None
    while True:
        data,markdown=summarize(args.project,args.campaign)
        encoded=json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
        if encoded!=previous:
            atomic(output/'summary.json',encoded)
            atomic(output/'summary.md',markdown)
            print(json.dumps({k:v for k,v in data.items() if k!='rows'},ensure_ascii=False),flush=True)
            previous=encoded
        if not args.watch or data['controller_finished']: break
        time.sleep(15)
