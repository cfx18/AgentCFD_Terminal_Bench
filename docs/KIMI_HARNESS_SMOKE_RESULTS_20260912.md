# Kimi-K3 × 四个 Harness：本轮烟测结果

执行已结束，没有待运行的模型请求。本轮正式选择：s-001 + 3 道历史改错题，
共 16 个组合。**14 个正式通过、1 个预算内未通过、1 个无有效答案的异常组合。**
这是接口烟测，不是模型能力排名；不能把两个不同任务的通过数合成物理准确率。

## 1. 三道改错题：12 / 12 通过

| Harness | simulationType：RAS → laminar | nu：1 → 0.01 | 恢复缺失 0/U | 模型请求合计 |
|---|---|---|---|---:|
| Codex | 通过，5 次 | 通过，6 次 | 通过，8 次 | 19 |
| FoamClaw | 通过，4 次 | 通过，5 次 | 通过，6 次 | 15 |
| Claude Code | 通过，15 次 | 通过，18 次 | 通过，13 次 | 46 |
| Kimi Code | 通过，6 次 | 通过，4 次 | 通过，5 次 | 15 |

题号依次为 `c-76ec558ecaf3dd15f849`、`c-3c8b63b3c25b0cb103eb`、
`c-6091937935d8d2963bfa`，来自已审阅 approved 清单，分别为 simpleFoam、
icoFoam、pimpleFoam。使用原缺陷断言，无 OpenFOAM 检查或 LLM judge。
缺失 0/U 的旧断言是结构性恢复检查，不等同于全部边界条件正确。

原始表：[改错逐题表](../runs/kimi-four-harness-smoke-001/scoreboard.md)。
该旧目录中 s-001 行属于已停止的协议诊断，不能与下面正式结果混用。

## 2. s-001：从零生成、真实求解、自行后处理

| Harness | 正式判定 | 模型请求 | 原生提交 / 成功跑完 | 无效动作提交 | 报告被拒 |
|---|---|---:|---:|---:|---:|
| Codex | 通过 | 12 | 1 / 1 | 2 | 0 |
| FoamClaw | 未通过，64 次预算用尽；验收存在争议 | 64 | 6 / 5 | 31 | 5 |
| Claude Code | 无有效答案，输出预算耗尽；程序归类为 error | 1 | 0 / 0 | 0 | 0 |
| Kimi Code | 通过 | 10 | 1 / 1 | 0 | 0 |

“无效动作提交”是未写/未正确提交动作文件，不是 OpenFOAM 字典报错。
API 工具循环次数不是 pass@3。原生次数不包括代码资格检查或旧协议诊断。

| Harness | 已提交报告的最大速度剖面误差（m/s） | 原始输出与自报值一致 | 物理量检查 |
|---|---:|---|---|
| Codex | 0.0013119655 | 是 | 全通过 |
| FoamClaw | 0.0008816332 | 是，5 份报告均一致 | 5 份报告均通过定量检查 |
| Claude Code | 无报告 | 不适用 | 未评估 |
| Kimi Code | 0.0008816332 | 是 | 全通过 |

速度误差阈值为 0.005 m/s；另验收 Uy RMS、终止时间、初始条件/物理配置。

### FoamClaw 为什么没有正式通过

1. 首次运行缺少 `pFinal`：原文 `Entry 'pFinal' not found in dictionary "system/fvSolution.solvers"`。
   模型根据原生日志修复，之后运行成功。这是配置缺项，不是数值发散；程序当前因
   已出现 `Solving for`，将其粗粒度归类为 numerical。
2. 其后 5 份报告的定量物理结果及数值真实性全通过，唯一失败项都是 `task_contract`。
   对应输入缺少空的 `mergePatchPairs ()`；OpenFOAM 接受该输入，但验收器要求显式存在。
   任务说明没有明确要求此可选项，故不能把这些失败解释成不懂物理。
3. 模型只收到 `task_contract=false`，随后猜测修改其他配置并多次只回复文字。
   第六次运行还把要求的 `(4 20 1)` 网格改为 `(8 40 1)`，此时另有明确的任务约束偏离；
   这次未提交可验收报告。不能将最后一版输入也笼统称为完全正确。
4. 第三次运行回收日志超时，退出码已持久化。通过同一运行 ID 回收后恢复原会话，
   累计预算不变。原中断和恢复证据都保留，未重跑已完成命令。

### Claude Code 为什么没有答案

原始响应为 HTTP 200，耗时 447.154 秒，`finish_reason=length`：

```json
{"completion_tokens":16384,"reasoning_tokens":16381,"content":"","tool_calls":null}
```

这里 `tool_calls:null` 表示响应中没有工具调用字段，以上是便于阅读的摘录，完整原文见下。
输出额度被推理消耗，最终无正文/工具调用。**不是 429、不是请求超时、不是 OpenFOAM 答错。**
适配器抛出 `Provider returned neither text nor tool calls`；上层原因笼统写为
`model_request_outcome_unresolved`，分类仍需改进。没有再次派发付费请求。
客户端收到错误后还在本地退避，核实无进行中请求后结束其沙箱进程；退出 -9 是人工终止，
不是模型或 API 自行崩溃。没有私下增加输出额度重测该组合。

原始响应：[response.raw](../runs/kimi-four-harness-science-002/trials/claude-code/s-001/agent/f88a8bc288194f2d92d9bf84c418eae7/submission-01/api/call-001/response.raw)。
其他逐题结果及恢复记录：[s-001 表](../runs/kimi-four-harness-science-002/scoreboard.md)、
[FoamClaw 逐次结果](../runs/kimi-four-harness-science-002/trials/foamclaw/s-001/run/scoreboard.md)。

## 3. 本轮修复与测试

- 修复动作重放：每轮记录并消费旧动作文件，只有模型新写的动作才能提交；文字回复不触发旧 run。
  修复前的 Codex s-001 诊断保留，不计入本表；四个正式 s-001 都使用同一 `fresh-action-v1`。
- 四种真实客户端连接本地假 API，验证文件工具、隔离、同会话恢复、相同动作显式重写及文字回复不重放。
- 全套 **163 passed，0 failed，0 skipped，77.06 秒**：
  [测试报告](harness-smoke-test-results-002.xml)。
- 真实 OpenFOAM 四项正负控制通过：有效输入、缺文件、错误物理、伪造测量值。
  [资格证据](../runs/harness-native-qualification-002/qualification.json)。
- 上述资格代码哈希：`5539924e06e6a2ed58c58cada5786b6c33c10bf567b7225aef309a3b19cf3986`。

本轮正式请求共 182 次（改错 95 + s-001 87）；另有旧动作协议诊断 22 次和连接探针 1 次。
这些是实际派发数，不是费用金额。无批量题库或其他模型在本轮被启动。

## 4. 实现与可比性边界

```text
agentcfd_bench/smoke/
├── campaign.py     题目冻结、串行执行、SQLite、结果表
├── agent.py        四种真实客户端、匿名工作区、会话与新动作提交
├── broker.py       唯一 Kimi-K3 上游、实际请求计数、原始收据
├── protocol.py     Responses / Anthropic / Chat 转换
├── foam_worker.py  沙箱内加载原 FoamClaw ReAct 源码
└── defects.py      旧改错断言
engine.py / runtime.py / tasks/s-001/tests/acceptance.py
                   原生运行、恢复、独立定量验收
```

采用 Codex 0.153.4、Kimi Code 0.28.1、Claude Code **2.1.0 Node 构建**。
FoamClaw 使用原 ReActEngine 的受控 shell/observation-only 配置，50 条历史，
关闭 executor push、跨题记忆和检索；不是原完整产品的所有工具能力。
Claude 辅助请求也计入预算。这不构成四种最新完整产品的能力排名。

桥接 skill 的隔离与显式模型身份要求用于本轮：匿名工作目录、隐藏参考/评分器、
宿主保存密钥、固定 Kimi-K3 请求与返回名检查，先无付费接口测试再实际调用。
返回名校验不能证明中转站实际使用的模型权重。

## 5. 暂不应扩大批量评测

先明确并修复三个边界：公开任务与验收文件/可选条目约束一致；输出预算耗尽不再
统称请求结果未知；已知终态错误立即终止客户端本地重试等待。保留当前原始成绩，
变更后的协议和再验收应另建版本，不覆盖本轮证据。
