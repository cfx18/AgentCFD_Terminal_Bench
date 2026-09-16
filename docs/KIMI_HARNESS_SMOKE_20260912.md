# Kimi-K3 × 四种 Harness：16 个烟测组合

改错结果：`runs/kimi-four-harness-smoke-001/scoreboard.md`，机器可读版本同目录
`scoreboard.json`。每题结束更新结果；单次 API 请求证据即时写入，不等整题结束。
该表是当前运行状态来源，本说明不复制一份可能过期的分数。

s-001 正式烟测使用 `runs/kimi-four-harness-science-002/scoreboard.md`。
001 中旧 s-001 的 Codex 试运行发现动作文件被重复消费：模型只回复文字时，
仍沿用上轮 `run`。已中断并保留旧证据，不将该次运行的提交数用于 harness 比较。
002 统一采用 `fresh-action-v1`：每轮先记录并移除旧动作，模型必须新写动作文件；
相同动作允许显式重写，缺动作只给格式反馈、不调用 OpenFOAM。验收阈值不变。
旧改错 12 个组合均通过，其最终文件提交协议不受该问题影响，不重复付费运行。

### 验收解释上的待审问题（不在运行中改判据）

- `tasks/s-001/tests/acceptance.py:physics_contract` 精确要求空 `mergePatchPairs ()`，
  `instruction.md` 未明确要求这个可省略项。FoamClaw 在 002 的第二次运行后报告中，
  数值真实性和全部定量物理检查通过，仅此项导致 `task_contract=false`。
- 同一检查器有额外输入文件白名单，但公开任务没有列出完整白名单。001 的诊断
  运行因此拒绝 `system/decomposeParDict` 等文件。不能据此直接判断物理知识不足。
- `runtime.classify` 用是否出现 `Solving for` 区分 startup/numerical。FoamClaw 的
  `pFinal` 缺项发生在首步已开始求解之后，故被记为 numerical；根因仍是配置缺项，
  不是证明数值不稳定。原生日志须与该粗粒度阶段标签一起审阅。
- 以上限制不通过更改答案或放宽当前判据掩盖；最终表保留正式结论，并另列定量检查。

### 002 执行异常与恢复凭据

- FoamClaw 第三次原生提交在读取 mesh-check 日志时 `TimeoutExpired`。退出码已先
  持久化，使用同一 `r-000003` 安全回收，已完成命令不重跑。后续通过正式 `resume`
  接口继续原会话；累计预算不重置。原中断记录保留于 `evidence/result.json`，恢复
  原因和新终态另存 `recovery-001/`，汇总 SQLite 更新为最后观察状态。
- Claude Code 首请求返回 HTTP 200，`finish_reason=length`；completion_tokens=16384，
  reasoning_tokens=16381，content 为空且无 tool_calls。它不是超时、429 或 OpenFOAM
  答错，而是本轮输出预算耗尽。当前适配器将其作为 `ValueError`，上层笼统标为
  `model_request_outcome_unresolved`，因此该总原因不够精确，应以原始响应为准。
  上游调用仅一次；适配器拒绝再次派发。客户端仍在本地退避，确认没有进行中的
  请求后结束其沙箱进程，让队列继续；退出 -9 属于这次人工结束，不能误判 API 崩溃。

## 冻结题目与验收

| 题目 | 求解器/任务 | 注入错误或目标 | 本轮验收 |
|---|---|---|---|
| c-76ec558ecaf3dd15f849 | simpleFoam 改错 | simulationType：RAS → laminar | 原有 defect-local 断言 |
| c-3c8b63b3c25b0cb103eb | icoFoam 改错 | nu：1 → 0.01 | 原有 defect-local 断言 |
| c-6091937935d8d2963bfa | pimpleFoam 改错 | 恢复缺失 0/U | 原有缺失速度场恢复断言 |
| s-001 | 瞬态 Couette 从零建模 | 建模、提交运行、后处理 | 真实 OpenFOAM + 原有物理量与报告真实性验收 |

前三题来自 `tutorial-release-v3/registry.json` 的 approved 清单，跨三个求解器和
三个错误类型。选择在模型运行前冻结，没有按新结果筛题。改错题不要求求解器
运行，不调用 DeepSeek judge；特别是旧缺文件断言不代表逐边界数值物理验收。
不将三题改错通过与 s-001 物理通过混成一个“物理正确率”。

## 固定模型、版本和范围

仅调用现有 provider 的 **Kimi-K3**；`.env` 中的 GLM-5 默认值不参与选模。
broker 校验请求与返回模型名，模型密钥只留宿主端。返回名校验不等于独立验证
中转站实际部署的权重身份。

| Harness | 实际实现 | 说明 |
|---|---|---|
| Codex | CLI 0.153.4 | 原生文件/shell 工具；Responses 转统一 Chat |
| FoamClaw | 原始 ReActEngine 源文件哈希冻结 | 受控 shell 工具；observation-only，50 条消息；关闭跨题记忆和 executor push |
| Claude Code | 2.1.0 Node 构建 | 2.1.133 原生构建在此隔离容器启动退出 250；未混用原生构建成绩 |
| Kimi Code | @moonshot-ai/kimi-code 0.28.1 | 独立安装的 Node 客户端，不是本机 Python kimi-cli 1.50.0 |

各 harness 保留自己的循环、会话和提示；额外预热/命令分类请求也计数。
这是受控输入和资源的接口烟测，不是完全相同内部工具集的消融，不代表四个
最新完整产品的质量排名。未人为加入解题示例或外部 OpenFOAM 文档检索。

改错：每题每 harness 一个样本、一次提交，最多 32 API 请求，模型墙钟 1200 秒。
s-001：沿用 64 API 请求、模型墙钟 3600 秒、原生总时间 600 秒、单次原生 120 秒。
请求超时 600 秒；输出上限 16384，与客户端请求的更低值取最小；未强制覆盖
thinking/temperature。全局串行。不能把多次 API 工具循环叫成 pass@3。

## 执行与监控源码

- `agentcfd_bench/smoke/campaign.py`：冻结选择、串行控制、SQLite 状态、结果表。
- `smoke/agent.py`：匿名工作区、真实客户端启动、会话恢复、退出证据、文件捕获。
- `smoke/broker.py`：单一 Kimi-K3 provider、实际派发计数、无隐式重试、原始证据。
- `smoke/protocol.py`：三种客户端协议转换，不改写任务文件或工具参数内容。
- `smoke/foam_worker.py`：仅在沙箱中加载原 ReAct 模块，注入传输与受控工具。
- `smoke/defects.py`：从旧版迁入的断言，未扩展/放宽判定。
- `engine.py / runtime.py / tasks/s-001/tests/acceptance.py`：沿用 s-001 执行与验收。

模型只得到 `/work`、当前会话目录和只读原生输出；不挂载参考、评测代码、
历史成绩、其他题目或宿主密钥。API 出错保存终态/未知态并继续其他组合，不
偷偷更换模型或把重试当首次样本。结果未知的请求不自动重发。

```bash
tail -F runs/kimi-four-harness-smoke-001/controller-repair.log
tail -F runs/kimi-four-harness-science-002/controller.log
python -m agentcfd_bench.smoke.campaign report --root runs/kimi-four-harness-science-002
```

逐题原始证据在 `runs/.../trials/<harness>/<task>/agent/<anonymous-id>/submission-*/`：
`events.jsonl`、`stderr.log`、`exit.json`、`client_result.json`、`api/call-*/`。
`request.json` 与 `wire_request.json` 可对照转换前后参数；`response.raw` 是原始
响应；只有 `complete.json` 证明收到请求终态。`private/` 仅供维护人员查看。

## 准入测试证据

- 防重放修复后全套 **163 passed，0 failed，0 skipped，77.06 秒**；见
  `harness-smoke-test-results-002.xml`。四客户端均测试连续新实例恢复、显式重写相同
  动作、仅文字回复不重复消费旧动作。
- 当前资格：`runs/harness-native-qualification-002/qualification.json`，四项控制通过；
  代码哈希 `5539924e06e6a2ed58c58cada5786b6c33c10bf567b7225aef309a3b19cf3986`。
- 以下 001 为修复前的历史准入证据，保留以对应原改错记录：
- 全套 **163 passed，0 failed，0 skipped，62.85 秒**；见 `harness-smoke-test-results.xml`。
- 四种真实客户端连接本地假 API，均完成工具改文件及新实例恢复同一会话；不拿
  假模型测试结果作为付费成绩。
- 当前代码 OpenFOAM 四项正负对照全通过，见 `runs/harness-native-qualification-001/qualification.json`。
- 资格代码哈希：`27736110628041854c295503134cb9daa6e3b37fd9b118ba8efb068191d8e2c6`。
- 修复的工程问题：禁止新 proc 挂载时使用隔离的 self/exe stub；Kimi print 不能
  与 auto/yolo 合用；识别 Kimi 原生消息终结格式；Claude 辅助请求不能漏计；
  补齐旧 Codex Chat 路由遗漏的转换模块；恢复时拒绝 harness 身份变更。
