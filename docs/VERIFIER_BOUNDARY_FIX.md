# 2026-09-13：验收与末轮提交边界修复

修复已应用主项目；不覆盖旧批次、不改数值容差、不增加模型单次输出 token 上限。
原任务题面、参考文件、模型和离线文档都未变。改变的是有缺陷的验收/提交实现，
以新的代码哈希和 `fresh-action-v2-budget-boundary` 冻结。主项目完整回归已通过
536 项，0 失败、0 跳过；五题重新原生资格全部通过。此文不是已完成全部付费评测的声明。

## 问题、修复与具体代码

| 问题 | 旧行为 | 新行为 | 代码 / 测试 |
|---|---|---|---|
| AMI 初始化误判 | 额外 value 项使整个边界字典比较失败 | cyclicAMI 的可选 value 作为初始化处理；保留 type、useImplicit、其他参数和全部最终场检查 | [science_contract.py](../agentcfd_bench/foam/science_contract.py)、[8 个正反例](../tests/test_ami_initialization.py) |
| 最后一次调用已提交仍丢报告 | 客户端随后达到预算上限，整轮 submitted=false | 仅 fresh-action 模式、确定本地预算终止且存在本轮新 action 时收取提交；内容仍由正常验收解析 | [smoke/agent.py](../agentcfd_bench/smoke/agent.py)、[真实客户端边界测试](../tests/test_terminal_action_budget.py) |
| 本地预算被当作可重试限流 | 本地无剩余调用返回 429，客户端继续退避 | 本地预算返回 400 invalid_request_error，独立记 budget_exhausted 凭据；真实上游 429 不改写为成功 | [smoke/broker.py](../agentcfd_bench/smoke/broker.py)、[预算测试](../tests/test_rounds_only_budget.py) |
| 新注册题目使旧单题测试失败 | 发布测试写死只允许 s-001 | 校验显式注册清单及完整结果，而不是固定单题数量 | [发布测试](../tests/test_release_checks.py) |

提交恢复不接受：上游故障、结果不明请求、超时、旧 action 或非法工作区输入。
不额外发送模型请求来补结束语，不把已消耗的调用计数归零。
实际四客户端分别测试有新 action、无新 action、旧快照模式；另测引擎最后一次
调用可正常验收及三种异常退出。测试使用本地假 API，不是模型得分。

## AMI 的单变量原生证据

只改原始 s-102 的 U/p 两侧 AMI：各加入 `value $internalField;`，其余配置完全不变。
使用已有独立运行环境和原始参考结果，不再次运行原参考。

| 项目 | 结果 |
|---|---|
| 原生 blockMesh / checkMesh / simpleFoam | 全部完成 |
| 终点 / 单元数 | 100 次迭代 / 24 |
| U relative L2 / Linf | 0 / 0 |
| p relative L2 / Linf | 0 / 0 |
| 最终 U/p 全部逐项相等 | true |
| 旧物理配置检查 | 错误地拒绝 4 个 AMI 条目 |
| 修复后独立验收 | pass |
| 模型调用 / 原参考重跑 | 0 / 0 |
| 集群作业 7941375 | 释放凭据存在，另查队列已终止 |

[完整评估](../runs/ami-initial-value-control-001/assessment.json)、
[原生命令、退出和输出](../runs/ami-initial-value-control-001/native/runs/r-000001/)、
[可重复调用的诊断入口](../ci_checks/ami_initialization_control.py)。
已有目录再次调用只观察/读取原操作；不得对结果不明的操作创建替代执行。
本控制证明这一初始化写法等价，不声称所有初始化、数值离散或网格都等价。

## 历史影响与新批次边界

旧批次 `runs/tutorial-science-matrix-001` 已终止，20 个试验全部留在注册分母。
6 个完成（4 pass、2 fail），1 个维护中断，13 个未开始。

- Codex/s-102：有一份有效末轮报告误计为格式失败。审计该报告仍未通过场误差，
  所以原最终失败结论不变，格式与报告次数必须采用明确单列的审计更正。
- FoamClaw/s-102：两份现有报告在修复后仍有数值偏差，但收到过错误的物理配置反馈。
  不能推断它在正确反馈下仍失败，不能用只读重判替代重新答题。
- Claude Code/s-102：维护中断前发了 1 次请求，后收到 HTTP 200；BrokenPipeError
  是响应无法送到已退出客户端，并非模型答案失败。不得自动重发或把调用数记为零。

详见[逐题原文和定量审阅](SCIENCE_PAID_OBSERVATIONS.md)。旧实现保存于
[冻结源码归档](../runs/tutorial-science-matrix-001/private/frozen-implementation-v1/)，
归档已验证匹配旧批次全部五题代码哈希；[本次精确补丁](verifier-boundaries-20260913.patch)可单独审阅。
旧批次用新实现恢复会明确拒绝，不会混合版本。

新批次 `runs/tutorial-science-matrix-002` 已登记同样 5 题×4 harness、Kimi-K3、
单并发、相同离线文档和 64 次累计 API 预算。准备阶段全部 queued、未付费启动；
其后用户已明确确认开始重测，独立控制器现已启动，见[002 观察记录](SCIENCE_MATRIX_002_OBSERVATIONS.md)。
原生资格使用新目录 `runs/tutorial-science-qualification-002`；原始正例只读导入，
不覆写 `tutorial-science-qualification-001` 的旧结论。
五题各六项检查全部通过，[原生资格表及合理数值变化的场误差](../runs/tutorial-science-qualification-002/report.md)。
15 个对照作业的释放凭据齐全，另查队列确认均不再活动；新批次 check_ready 通过。
旧批次累计发出 217 次模型请求；新批次从零独立计数。重新从头跑这 20 个试验会产生
额外付费调用，每题仍最多 64 次，总上界 1280 次（包含客户端辅助请求）；已按用户确认启动。

## 回归记录

- 末轮提交针对性验证：51 passed；[JUnit](terminal-budget-boundary-final-tests-20260913.xml)。
- 第一遍隔离副本全回归：532 passed、4 failed；[完整失败记录](verifier-boundary-full-tests-20260913.xml)。
  一项为旧单题注册断言，三项为临时副本缺少历史改错测试数据；未删除或跳过这些测试。
- 补齐只读夹具并修复断言后的相关复测：36 passed；[JUnit](verifier-boundary-followup-tests-20260913.xml)。
- 主项目完整回归：536 passed、0 failed、0 errors、0 skipped，371.30 秒；
  [原始 JUnit](verifier-boundary-production-full-tests-20260913.xml)。
  包含 16 项末轮预算测试、8 项 AMI 正反例，以及 20 项五题×真实四客户端接口测试。
  [新批次绑定的测试凭据](../runs/tutorial-science-matrix-002/private/tests.json)。

重新付费启动需要通过修复版资格检查；先保留旧证据，再明确新批次和额外调用，
不能把重测伪装成首次尝试，也不借此启用被排除的模型或旧改错任务。
