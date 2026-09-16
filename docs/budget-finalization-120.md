# 120 次调用与预算末尾验收

本轮只改预算／收尾协议，不改变公开观测、GT、物理误差算法或 reward 阈值。
新配置为 `experiments/dense-reconstruction-astra-120.yaml`；旧实验不被覆盖或原地续接。

| 层 | 实现 | 变化 |
|---|---|---|
| 配置 | `tasks/experiment.py` | `native_seconds: null`；显式收尾策略；旧配置默认行为不变 |
| 原生执行 | `execution/runner.py`、`worker.py` | 可无限时，保留取消／真实退出证据；派发顺序不依赖 UUID 或文件时间 |
| Harness | `harnesses/codex.py`、`kimi.py` | 无限时模式不再推导整个 CLI 超时；仍计所有真实 API 调用 |
| 调度 | `controller.py` | 将“调用耗尽”与“评分失败”拆开；不追加总结调用 |
| 收尾 | `finalization.py` | 显式提交优先，否则最后成功 `run`；只回收已有结果，不启动新求解 |
| 验收 | `grading/service.py`、`dense_native.py` | 复用原验收，不放宽终点、完整性或精度要求 |
| 报告 | `reports/summary.py` | 同时显示调用数、停止原因、选择来源、物理结果及中间分 |

代码路径均相对于 `agentcfd_bench/`。

## 三种典型结果

- 120 次耗尽，最后成功运行物理 reward 为 0.5：保留 **0.5**，停止原因另记调用耗尽。
- 120 次耗尽，既无显式提交也无成功 `run`：模型结果失败，原因是没有可验收计算，不是机械的预算零分。
- 120 次耗尽，最新作业退出证据缺失：中断／error，不从更早结果补造分数。

若最后成功运行只是一个很短的诊断，它可能因不包含题目要求的终点而得零。
这是公开的选择／验收规则，不是按 GT 挑解。Agent 可在预算内显式提交较早结果。

## 恢复与统计口径

先持久化 finalizing 状态，再回收原生操作、冻结选择、验收、保存摘要，最后提交终态。
验收结果写入而状态未提交时，恢复复用同一选择和评分收据，不调用模型。
`summary.json` 仅汇总已记录事实，完整可见操作仍在实时 transcript 中；不声称取得隐藏思维链。

取消累计／单次默认求解时限与整题墙钟期限，但保留：

- 单次 API 600 秒无响应保护；不是模型探索预算。
- 内存和文件大小安全限制。
- 独立 grader 采样的 300 秒故障保护；失败归基础设施错误，不直接扣物理分。
- Agent 自愿给某条命令设置的期限和显式取消。

## 测试证据

新增测试覆盖自动选取、显式提交优先、最新失败／准备命令跳过、CLI 非零退出的预算耗尽、
部分分保留、无结果、未知请求不补发、记录未提交时恢复、日志未回收时恢复、证据损坏拒绝。
真实 Codex CLI 的订阅／自定义 API 与 Kimi Code 均用本地假服务验证有限／无限时分支，
不消耗付费模型调用。原生 OpenFOAM 采样另行回放已有 GT 字段，不推进物理时间。

全套回归：213 项通过、0 失败／跳过，285.99 秒，见
`docs/budget-finalization-tests-20260916.xml`。
随后补充的真实 CLI 边界／恢复测试：12 项通过、0 失败／跳过，80.27 秒，见
`docs/budget-finalization-extra-tests-20260916.xml`（与全套有重复覆盖，不简单相加）。
原生 GT 回放：`audits/dense-native-budget120-20260916-001/validation.json`。
两题覆盖率均为 100%，最大绝对差不超过 5.69e-14；没有模型调用或求解器推进时间。
新任务发布重新绑定上述测试与当前执行代码；不是翻转旧 release 的资格标记。

`prepare experiments/dense-reconstruction-astra-120.yaml` 已返回 `ready: true`、
`blockers: []`、`paid_calls: 0`。本次修改／验证没有启动新的付费评测。
