# Kimi Code + 官方 Kimi K3：新版四题实验

配置：[workbench-v3-kimi-official.yaml](../experiments/workbench-v3-kimi-official.yaml)。

独立后台控制器于 **2026-09-16 03:23:45 UTC** 启动，PID **1573771**。
实验目录：`runs/workbench-v3/20260916T031559.893897Z-ab03d48c`。
启动身份及原始进程记录见该目录 `launch.json`；退出聊天不会主动停止它。
同一时期的 Astra 目录 `20260916T022031.171364Z-1ff93ae2` 没有重启或覆盖。

| 项目 | 本轮条件 |
|---|---|
| Harness | 已安装的 Node `@moonshot-ai/kimi-code@0.28.1`，不是 Python kimi-cli |
| API / 模型 | `https://api.moonshot.cn/v1` / `kimi-k3`，无中转或模型回退 |
| 任务 | s-205 → s-203 → s-202 → s-204，每个实验内部串行 |
| 任务版本 | `workbench-v3-polyhedral-v2`，与 Astra 实验相同 |
| 每题预算 | 总共 64 次模型请求、1000 秒原生命令，网络请求 deadline 600 秒 |
| 资料 | 同一冻结离线 OpenFOAM 文档，无互联网；GT、评分代码不挂载 |
| 隔离 | 与 Codex 共用 OS namespace、原生工具 RPC、不可覆盖收据和实时 transcript |
| 会话 | 同题原生 Kimi 会话续接；不同题独立工作区，没有跨题记忆 |
| 子 Agent | 原生 permission deny；WebSearch 未注册，没有外部搜索服务 |

官方 `/models` 返回的上下文窗口是 1,048,576，默认 reasoning effort 为 `max`。
元数据证据见 `audits/kimi-workbench-v3-20260916T031255.320758Z/official-model.json`。
上下文窗口提供给原生客户端管理压缩，不是评测总 token 消耗上限。
基准不注入输出 token 上限；本地实测 Kimi Code 自行发送 `max_tokens=131072`，
桥接原样保留，不额外降低。采样／思考参数及工具历史均保留。
当前 Chat broker 完整接收 JSON 后再向客户端提供 SSE；这不是上游原生流式透传，
原始结果、返回状态、交付记录与未知结果均单独保存。未知请求不自动重发。

## 工程验证

`tests/test_kimi_local_api.py` 的 8 项测试使用真实 Kimi Code 与本地假 API：

- 读文档、写文件、原生失败日志返回、同一会话续接；
- 畸形上游结果、上游 503、调用预算耗尽；
- 模型／客户端身份与 endpoint 不允许静默替换；
- 连接在返回前断开：未知结果保存，禁止自动重发；
- 子 Agent 被拒绝、网页搜索不可用；
- 真实 OpenFOAM 小算例完成 `blockMesh → setFields → rhoCentralFoam → submit`。

这些是假 API 工程检查，不是 Kimi 的解题成绩。
全项目回归记录：`docs/v3-kimi-tests-final-20260916.xml`。
此次全套回归 **168 passed，0 failed / skipped**。
归档期间另一路开发修改了当前工作树的稠密观测预算 reward 分支及对应测试，
启动保护因此先暂停，没有付费请求。没有把该分支热补进本轮快照；随后从本轮
冻结代码重新执行原成功测试清单中的 **28 项接口／控制器测试，28 passed**。
证据：`docs/v3-kimi-frozen-approved-20260916.xml`，及运行目录 `qualification/`。
四题注册清单没有删减；后加的稠密 reward 测试不属于该冻结版本的接口清单。
最初混用新测试的记录仍保留为 `docs/v3-kimi-frozen-interfaces-20260916.xml`，
其中唯一失败是新测试要求旧快照尚不存在的稠密 reward 功能，不是本轮四题成绩。

## 自行启动与查看

```bash
cd /root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench
../.venv-eval/bin/python -m agentcfd_bench prepare experiments/workbench-v3-kimi-official.yaml
# 下条命令创建新实验；不要用它查看已有进度，也不要重复启动。
../.venv-eval/bin/python -m agentcfd_bench run experiments/workbench-v3-kimi-official.yaml --allow-paid
../.venv-eval/bin/python -m agentcfd_bench report /absolute/run/directory
```

已经启动的本轮请直接查看，不要重复运行 `run`：

```bash
../.venv-eval/bin/python -m agentcfd_bench report runs/workbench-v3/20260916T031559.893897Z-ab03d48c
tail -F runs/workbench-v3/20260916T031559.893897Z-ab03d48c/trials/s-205/transcript.md
```

每题 `transcript.md` 是实时中文栏目 I/O；`native/r-*/stdout.log` / `stderr.log`
是原生日志，`grading/result.json` 是最终私有评分。
配置、任务、代码、文档快照都保存在新的 UTC 时间目录。运行时凭据仍只从宿主读取。
每次恢复校验冻结代码、客户端版本／依赖文件及本地 Node、隔离工具指纹。

Kimi Code 原生提示词和工具与 Codex 不同，这轮比较的是 Harness + 模型组合，
不能仅归因于模型本身。原生 CLI 来源与配置机制见
[Kimi Code 官方仓库](https://github.com/MoonshotAI/kimi-code)。
