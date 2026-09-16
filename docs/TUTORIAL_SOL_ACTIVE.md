# 当前作者任务：GPT-5.6 Sol / high

2026-09-16 用户确认由 Luna 切换至 Sol。本文件只描述当前出题工作，不是模型评测成绩。

- 模型：`gpt-5.6-sol`；推理档位：`high`；Codex 原生子 Agent 禁用。
- 账号：`/root/.codex-experiment` 订阅，主机 broker 持有凭证，不改 API、不复制凭证到沙箱。
- 新批次：`runs/tutorial-authoring/20260916T091416Z-sol-high-sca-shared10-v1/`。
- 本轮 90 题：40 题有明确 Luna 过载失败回执，作为 Sol 独立新尝试；50 题此前未启动。
- 原注册 100 题中，本地已开始的 10 题继续保留；全部 515 条来源注册表也保留。
- 原始题目、物理条件、验收标准不变。题面仅更新作者型号和远程环境确实提供 helper 的说明。
- 每题最多 120 次模型调用；token/成本统计而非截断。每个新尝试单独计数，旧请求没有消失。
- 最多 10 个作者并行；native 共用一个 64 核 Slurm allocation，最多 10 个独立单核 step。
- 远程写入仅在 `/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/authoring/20260916T082025Z/`。

## 直接看进度和 IO

[实时中文总表](../runs/tutorial-authoring/20260916T091416Z-sol-high-sca-shared10-v1/PROGRESS.zh.md)
包含每题的交互状态、接口异常、作者结论和中文审阅/轨迹链接；每五分钟或每题结束时自动更新。
不需要主 Agent 持续监控，不需要用户再回复才能开始下一批。

在 `AgentCFD_Terminal_Bench` 下执行：

```bash
../.venv-eval/bin/python -m agentcfd_bench.authoring.control status runs/tutorial-authoring/20260916T091416Z-sol-high-sca-shared10-v1/campaign.json
tail -F runs/tutorial-authoring/20260916T091416Z-sol-high-sca-shared10-v1/controller.log
```

已启动，不要重复 `launch`。每题实时 IO 是 `workers/<题号>/agent/transcript.md`，实际模型请求在
`workers/<题号>/agent/calls/turn-*/api/call-*/wire_request.json`，native job/step/日志在该题 `native/r-*`。
配置和切换来源完整保存于 `campaign.json`、`model-switch.json`、各 worker 的 `config.snapshot.json`。

Luna 原控制器 PID 1857542 已退出。其 `superseded.json` 指向 Sol 批次，旧入口拒绝再次启动；
没有取消进行中的模型请求或旧本地 native 计算。Luna 的旧共享池未申请过节点，现已关闭接单。

## 相关实现与检查

- `authoring/switch_model.py`：新建批次、区分重试与未启动、保留来源、拒绝未知请求/重复切换。
- `authoring/worker.py`：明确授权的 Sol/high/账号组合，拒绝在已有历史中替换配置。
- `authoring/migration_gate.py`：正确识别恢复后的控制器，先禁止新派发，再收尾退出。
- `authoring/control.py`：独立后台、过载冷却、旧批次退出保护。

本次模型迁移不安装客户端、不重写工具协议。原生执行共享池此前已经过真实远程集成测试；
Sol 的真实联通必须看本批请求结果，不能用 Luna 或假模型回执代替。
完整回归 **313 项通过**（344.62 秒）：`docs/tutorial-sol-switch-tests-20260916.xml`。
随后新增的重复切换拒绝测试也通过；针对性回归另有 45 项通过的独立记录。

### 本次实际联通记录（2026-09-16 09:17 UTC）

- 141 次 `response.completed` 的服务端型号均为 `gpt-5.6-sol`；已检查的 wire 请求推理档位均为 `high`。
- 作者首批 10 题并行工作，尚不能称为 10 道已完成的题。
- Slurm 作业 `7957351`，节点 `ea0604`，`RUNNING / Nodes=1 / CPUs=64`。
- 已回收 21 次独立 native 操作：退出 0 共 19 次、退出 1 共 2 次；这些是步骤，不是通过题数。
- native 传输错误记录为 0；非零命令结果照常返回给作者，不伪造成成功。
- 针对性回归 45 项通过：`docs/tutorial-sol-switch-targeted-20260916.xml`。

`completed` 只代表作者交互结束，`candidate` 仍是待核验材料；二者均不等于已发布或物理通过。
