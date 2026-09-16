# 管线故障审计：2026-09-14

## 结论与范围

**管线确实可能制造假失败、假通过、额外调用和“还在运行”的假象。**
本轮区分了历史上已经发生的误拒，与故障注入才复现的潜在故障，不能把所有
旧失败都归给管线。没有调用付费模型、启动 OpenFOAM、提交集群作业或改写旧成绩。

审计对象是当前 `AgentCFD_Terminal_Bench` 的任务加载、四 harness 共用桥接、
独立 Codex 桥接、提交、验收、调度、恢复和报告。未将父项目归档改错管线
重新上线；也不宣称验证了任意新任务或上游服务的全部行为。

按 `bridge-benchmark-harness` 技能要求，完整回归启用真实 Codex CLI、
Claude Code、Kimi Code 和受控 FoamClaw，连接本地假 API，检查隔离、
工具执行和会话恢复；不把纯 mock 测试称为真实客户端适配测试。

## 本轮修复的八类问题

| 问题 | 旧实现的具体后果 | 修复与回归测试 |
|---|---|---|
| 验收器异常归咎模型 | checker 的 `KeyError` / `ValueError` 被当作 `native_output_not_extractable`，不断给失败反馈，最后耗尽模型轮次；其他异常可能逃出控制器 | `evaluation.py` 区分显式输出解析拒绝与 checker 异常。`test_verifier_exception_is_not_a_model_failure` 覆盖四种异常，要求 error、三次调用停止、零答案失败 |
| 不完整的 pass 被接受 | checker 返回 `pass`，即使检查项缺失、为假或不是布尔值也可能通过 | `validate_result()` 要求所有预登记检查项存在且为真。六个异常结果回归，不把程序错误变成 pass 或模型 fail |
| 已存验收结果仍重算 | result 已落盘而 SQLite 未提交时，恢复会再次调用 checker | `evaluate_once()` 绑定 action、native、task 哈希；恢复读取同一结果。回归证明只调用一次、历史不重复，并拒绝换提交后复用结果 |
| 终态被旧单题状态覆盖 | campaign 已将异常记为 interrupted，报表又用单题遗留 running 覆盖 | 已提交的调度终态优先；新增 `all_trials_terminal`，不偷换旧 `rates_are_final` 含义 |
| 故障处理自身再次崩溃 | runner 异常后读取损坏单题 DB 再次异常，整批剩余题目停止 | `_trial_snapshot()` 显式记录 `snapshot_error`，继续其他题，终态仍保留原始 `error_type` |
| 把普通异常当作原生排队 | 只要 phase 是 native 就反复进入 runner，异常也可能被重复“观察” | 仅 `native_outcome_unresolved` 才进入既有原生操作观察；其余异常终止该题。回归确保矩阵 20 项各调用一次 |
| 独立 Codex 的本地 429 和失败后转发 | 本地预算耗尽伪装成限流；失败后客户端再次请求仍可能发到上游。共用 broker 已修，独立分支未同步 | 本地终止返回非重试 400；预算有独立凭据；失败锁止后不转发。真实上游状态仍原样存在 http/complete/error 凭据，不改写成 400 |
| 独立流式分支把 EOF 当成功终态 | 空流或 incomplete 响应结束后仍允许继续转发 | 保存真实流后校验模型终态；空、失败、不完整响应锁止后续转发，不制造 completed 或补造输出 |

具体源码：

- [统一验收边界](../agentcfd_bench/evaluation.py)：`native_output_reader`、`validate_result`、`evaluate_once`。
- [会话调度](../agentcfd_bench/engine.py)：report 动作调用持久化边界，error 中止且不计为答案失败。
- [矩阵调度及报表](../agentcfd_bench/science_campaign.py)：`_trial_snapshot`、`report`、`execute`。
- [独立 Codex broker](../agentcfd_bench/adapters/codex_broker.py)：预算拒绝、失败锁止、流式终态。
- [全部新增回归](../tests/test_pipeline_audit.py)：24 项参数化测试，包括正向保护，**不是 24 个独立 bug**。

旧 `s-001` 的任务文件没有被编辑：只在加载时给其 `extract()` 加类型边界。
五道 tutorial 的 `snapshot()` 同样把既有解析拒绝标为 `NativeOutputError`。
这不意味着所有解析器 ValueError 都能自动证明物理错误；它只表示输出不符合
已支持的解析契约，解析器自身的正确性仍需依靠回归和真实原生对照。

`all_trials_terminal` 只说明注册试次均为 completed/interrupted，不代表所有题均
有可评分结果，也不单独证明控制器退出或远端资源释放；后两者仍须检查独立凭据。

## 历史问题：已经发生，不只是故障注入

- `s-103 / Codex`：合法 `RAS/model` 别名被误拒；首次合格报告发生于第 33 笔
  API 后，最终用了 64 笔。其后 31 笔受错误反馈影响，不能解释为纯能力不足。
- `s-104 / Kimi Code`：显式写出未改变的默认湍流系数被误拒；第 18 笔后的
  首报告本应通过，之后继续执行并遇到请求异常。
- 工作根目录/新鲜 action 说明歧义、文档与模型请求共用服务队列、本地可重试
  状态引发无效退避，都已在 Build-006 修复，本次重新检查其回归。

历史审阅仍是 **7 / 20**（原始 5 通过，另 2 次首报告误拒）；这是旧证据审阅，
不是修复版重测成绩。未交报告不会被本轮自动补分。
完整出处：[终局审阅](SCIENCE_MATRIX_002_FINAL_REVIEW.md)、
[逐题行为证据](SCIENCE_MATRIX_002_OBSERVATIONS.md)、[Build-006 修复记录](SCIENCE_RELEASE_006.md)。

## 验证记录

1. 修复前原有完整回归：758 passed、0 failed、0 skipped，源码与 Build-006
   一致，487.11 秒。说明“已有测试都绿”不代表边界完备。
2. 新增第一组：17 个旧代码故障注入全部失败；随后流式补充中空流和 incomplete
   两个场景失败，正常流和 HTTP 拒绝对照通过。首次沙箱测试中的 socket 权限
   错误不作为管线证据，已在允许本地 socket 的环境重新验证。
3. 修复后相关模块测试：121 passed；最后一轮接口/新增回归：54 passed。
   两组重叠，不能相加当作独立测试数。
4. 六项原生发布驱动的无执行测试全部通过：解析、故障观察、截止、不重复操作。
   没有因此执行任何原生作业，也不把这六项混进完整 pytest 计数。
5. 18 份实际报告通过新持久化边界重放。原始 frozen 结果与旧记录逐项一致；
   已审阅的静态契约修正结果与 Build-006 审阅也逐项一致。两种对照共 36 次
   检查，不是 36 份报告；输入证据哈希前后不变。
6. 修复版第一轮完整回归：781 passed、1 failed、0 skipped，失败仅为旧测试
   仍断言本地预算返回 429。仅同步该测试为 400 后，再次完整执行：
   **782 passed、0 failed、0 skipped，490.62 秒**。其中包含 24 项新增回归及
   四种真实客户端的隔离/恢复、五题 × 四客户端的端到端接口验证。
   源码在测试期间未变、与冻结候选一致、越界网络/执行尝试为零。
   这里的客户端连接本地假 API，原生服务使用假执行器，不是新的模型成绩。

证据目录：

- [修复前完整测试](../runs/pipeline-audit-20260914-baseline-001/summary.json)
- [真实复现失败记录](../runs/pipeline-audit-20260914-baseline-001/new-regressions-red-verified.xml)
- [补充流式复现](../runs/pipeline-audit-20260914-baseline-001/stream-red.xml)
- [修复后定向测试](../runs/pipeline-audit-20260914-baseline-001/targeted-green2.xml)
- [第一轮完整记录（保留旧断言失败）](../runs/pipeline-audit-20260914-fixed-001/summary.json)
- [最终完整测试汇总](../runs/pipeline-audit-20260914-fixed-002/summary.json)
- [最终完整 JUnit](../runs/pipeline-audit-20260914-fixed-002/junit.xml)
- [历史报告重放](../runs/pipeline-audit-20260914-replay-001/summary.json)
- [只读重放驱动](../ci_checks/audit_pipeline_reports.py)

## 尚不能说“管线永不出错”的边界

| 类别 | 本轮判断 |
|---|---|
| Ceph 文件系统等待 | 本轮再次观察到测试及只读查询处于 `ceph_mdsc_wait_request`。后来原进程恢复，没有重复启动。应用层修改不能消除文件系统服务故障；若要将活动证据迁到本地磁盘并归档，需要单独设计落盘/同步恢复协议 |
| 上游超时、截断、限流 | 只能正确记录、停止不安全重放，不能承诺修复服务商。8192 token 截断未发现是本轮注入的上限；客户端主动请求的上限保持原样 |
| FoamClaw 的 50 条历史窗口 | 属于当前受控 harness 的冻结配置，会影响任务记忆；不是这次擅自替换其记忆策略的理由 |
| Claude 辅助请求消耗轮次 | 当前按真实模型请求总数统计。改变为只计主解题调用会改变比较协议，未擅自改 |
| 耗时指标解释 | `model_seconds` 是 Agent 阶段耗时，包含客户端工具、请求等待和证据处理，不能等同纯模型推理时间；本轮没有通过重命名或更改预算来改变历史记录 |
| 跨厂商 API 的全部语义 | 当前是窄 text/function 桥接，不是全功能无损代理。检查到 Codex 首请求包含 `parallel_tool_calls=true` 和 `reasoning.summary=auto`，而共用 Chat 转换未转发它们；原始/转换后请求都有记录，但语义影响未验证。额外采样参数也并非全部有映射。这是明确的接口覆盖缺口，本轮没有扩展厂商参数映射或据此重算成绩，不能称各官方产品默认能力已完全等价 |
| 固定离散参考的物理限制 | 数值距离是在既定网格/基线上的验收，不是实验真值或网格无关证明；没有通过调整阈值消除真实数值失败 |
| 部署/重测资格 | 执行协议源码哈希已变；旧付费会话和旧原生资格不能拿来直接续跑。当前没有新的付费就绪声明，原生门禁需另行明确授权 |

任务、参考、验收阈值、文档包、模型名单、总轮次与输出预算策略均未改变。
没有在本轮增加 reward 系统、检索能力、模型输出上限或自动付费重测。

## 重复验证命令

从父项目目录运行，`--output` 必须换成不存在的新目录；完整测试驱动禁用真实
凭据，禁止外部网络、SSH 和原生命令，打开真实客户端本地假 API 测试。

```bash
.venv-harbor/bin/python -B AgentCFD_Terminal_Bench/ci_checks/check_deployed_release.py \
  --candidate AgentCFD_Terminal_Bench/review_candidates/pipeline_audit_20260914_002/project \
  --closure AgentCFD_Terminal_Bench/runs/tutorial-science-matrix-002/review/closure-002 \
  --campaign AgentCFD_Terminal_Bench/runs/tutorial-science-matrix-002 \
  --output AgentCFD_Terminal_Bench/runs/pipeline-audit-check-NNN
```

该命令只做测试，不是 paid-ready 发布命令。源码变更后必须重新冻结候选，
不能改写旧候选或在测试过程中继续修改受测源码。
