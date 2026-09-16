"""Expert-readable view of author receipts. No model, native job or regrading."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ..records.store import read
from .control import status, overloaded_jobs


def markdown(config_path):
    config = read(config_path)
    root = Path(config['root'])
    state = status(config_path)
    rows = []
    counts = Counter()
    overloads = set(overloaded_jobs(config, config['jobs']))
    activity = ''
    latest = root / 'progress.latest.json'
    if latest.exists():
        try:
            event = read(latest)
            if event.get('event') == 'provider_overload_cooldown':
                until = datetime.fromtimestamp(event['until'], timezone.utc).isoformat()
                activity = f'后台状态：上游服务过载，冷却至 {until}；到期自动继续未启动题，已有请求不重发。'
            else:
                activity = f'后台最近事件：{event.get("event")}；记录时间：{event.get("time")}。'
        except (ValueError, OSError, KeyError):
            activity = '后台状态文件正在更新；以原始请求和退出回执为准。'
    for job_id, job in config['jobs'].items():
        work = root / 'workers' / job_id / 'agent/work'
        path = work / 'author-result.json'
        try:
            result = read(path) if path.exists() else {}
        except (ValueError, OSError):
            result = {}  # author may still be writing; no fabricated conclusion
        if not isinstance(result, dict):
            result = {}
        lifecycle = state['workers'][job_id]['lifecycle']
        author_status = result.get('status', '尚无结论')
        harness_path = root / 'workers' / job_id / 'result.json'
        harness = read(harness_path).get('harness', {}) if harness_path.exists() else {}
        infra = state['workers'][job_id].get('infrastructure_error')
        interface = ('上游服务过载' if job_id in overloads else
                     '基础设施异常，可独立重试' if infra and infra.get('retryable') else
                     '接口异常，材料存在，需审阅' if infra else
                     '接口异常，见轨迹' if harness.get('errors') else '—')
        counts[author_status] += 1
        source = job.get('candidate', {}).get('inventory_source_path', '证据校验库')
        blocks = '; '.join(str(x) for x in result.get('blockers', []))[:300].replace('|', '\\|').replace('\n', ' ')
        report = work / 'REVIEW.zh.md'
        transcript = root / 'workers' / job_id / 'agent/transcript.md'
        link = f'[中文审阅]({report})' if report.is_file() else (f'[实时轨迹]({transcript})' if transcript.is_file() else '未开始')
        rows.append(f'| {job_id} | {source} | {lifecycle} | {interface} | {author_status} | {blocks or "—"} | {link} |')
    return '\n'.join([
        '# Tutorial 出题与 GT 准备进度', '',
        f'模型：`{config["model"]}`；账号目录：`{config["harness"]["auth_home"]}`。', '',
        '这里统计的是作者参考准备，不是受评 Agent 得分。candidate 是作者模型的待核验建议，**不等于已发布或已通过独立物理验收**。', '',
        activity, '',
        f'已观察到上游过载的作者任务：{len(overloads)}。completed 仅表示交互结束；接口错误不能算出题成功。', '',
        f'目标：{config["target_qualified_tasks"]} 道合格题；本队列：{len(rows)} 个作者任务。', '',
        *([f'本轮从 {config["model_switch"]["source_model"]} 切换至 {config["model_switch"]["target_model"]}。'
           f'已结束但缺材料的题为独立新尝试，未开始题直接接续；不覆盖或改名旧记录。'
           f' [切换清单]({root / "model-switch.json"})。', ''] if config.get('model_switch') else []),
        *([f'本轮是迁移后的远程队列。原注册 {config["migration"]["original_attempt_count"]} 题；'
           f'{len(config["migration"]["preserved_local_jobs"])} 题保留在原本地记录，未重复请求。'
           f' [原队列进度]({Path(config["migration"]["source_config"]).parent / "PROGRESS.zh.md"})。', '']
          if config.get('migration') else []),
        '| 编号 | 来源 | 交互生命周期 | 接口情况 | 作者结论 | 阻断原因 | 审阅入口 |',
        '|---|---|---|---|---|---|---|', *rows, '',
        '每题的原始来源、模型请求/响应、决策摘要、命令、退出码及 native 输出分别保存。没有退出/场量证据的题不能计作成功；未收敛、物理矛盾和基础设施错误需要分别归因。', '',
    ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    print(markdown(args.config))
