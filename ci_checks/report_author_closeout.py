"""Read author-native journals only. Never run missing work or grade an agent."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

import yaml

from agentcfd_bench.journal import read_receipt
from agentcfd_bench.task_package import PROJECT


def report(config, project=PROJECT):
    if config.get('version') != 'author-native-closeout-v1':
        raise ValueError('Explicit author-native report configuration required')
    rows, seen_tasks = [], set()
    for task in config['tasks']:
        if task['id'] in seen_tasks:
            raise ValueError('Duplicate registered task')
        seen_tasks.add(task['id'])
        operations, seen_paths = [], set()
        for root in task['evidence_roots']:
            directory = (project/root).resolve()
            if not directory.is_relative_to(project.resolve()):
                raise ValueError('Author evidence must stay within this project')
            # A caller chooses evidence roots explicitly. No filesystem discovery
            # can add a new benchmark task or silently replace an earlier attempt.
            for path in sorted(directory.rglob('spec.json')) if directory.is_dir() else []:
                run = path.parent
                if (not re.fullmatch(r'r-[0-9]{6}', run.name)
                        or run.parent.name != 'runs' or run.parent.parent.name != 'native'):
                    continue
                if run in seen_paths:
                    continue
                seen_paths.add(run)
                identity = run.relative_to(project).as_posix()
                try:
                    spec = read_receipt(path)
                    if spec['task']['id'] != task['id']:
                        raise ValueError('Task ID differs from its evidence configuration')
                    result = read_receipt(run/'result.json')
                    row = {'source': identity, 'run_id': run.name,
                           'input_hash': spec['input_hash'], 'seconds_limit': spec['seconds'],
                           'execution_task_version': spec['task']['version']}
                    if result is None:
                        exited = [p.stem for p in sorted(run.glob('*-exit.json'))]
                        row.update(status='unresolved', verdict='not_evaluated', recorded_exits=exited)
                    else:
                        if result['input_hash'] != spec['input_hash'] or result['task'] != spec['task']:
                            raise ValueError('Native result/input identity differs')
                        row.update(status='completed', verdict=result['verdict'],
                                   stage=result['stage'], reason=result['reason'],
                                   native_seconds=result['native_seconds'])
                    operations.append(row)
                except (ValueError, KeyError, TypeError) as exc:
                    operations.append({'source': identity, 'status': 'evidence_error',
                                       'verdict': 'error', 'detail': str(exc)})
        counts = Counter(row['verdict'] for row in operations)
        rows.append({'id': task['id'], 'title': task['title'], 'operations': operations,
                     'operations_registered': len(operations), 'native_verdicts': dict(sorted(counts.items())),
                     'native_seconds': sum(row.get('native_seconds', 0) for row in operations),
                     'formal_release': 'not_inferred_from_execution'})
    return {'version': config['version'], 'name': config['name'], 'registered_tasks': len(rows),
            'model_requests_sent_by_report': 0, 'native_jobs_started_by_report': 0, 'tasks': rows,
            'note': 'Native pass is execution completion, NOT physical qualification or an Agent score.'}


def markdown(value):
    lines = ['# 自主网格作者计算：只读运行表', '',
             '这里的通过/失败指 OpenFOAM 执行；物理反例运行成功恰恰可能是预期。不是 Agent 成绩。', '',
             '|题目|已登记原生操作|执行完成 pass|执行失败 fail|错误 error|结果未回收|原生累计秒|',
             '|---|---:|---:|---:|---:|---:|---:|']
    for row in value['tasks']:
        counts = row['native_verdicts']
        lines.append(f"|{row['id']} {row['title']}|{row['operations_registered']}|{counts.get('pass',0)}|"
                     f"{counts.get('fail',0)}|{counts.get('error',0)}|{counts.get('not_evaluated',0)}|"
                     f"{row['native_seconds']:.2f}|")
    lines += ['', '结果未回收不等于求解器仍在运行；请查看对应操作的 start/exit/released/result 记录。',
              '重复失败尝试保留，按证据路径区分；本表不自行合并成通过，不触发重试或补算。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='New JSON snapshot; refuses overwrite')
    parser.add_argument('--markdown', action='store_true')
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    value = report(config)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        with args.output.with_suffix('.md').open('x') as handle:
            handle.write(markdown(value))
    print(markdown(value) if args.markdown else json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
