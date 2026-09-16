# s-203 / s-204：管线恢复修复与验证

本轮只修执行、证据回收和显式续接，不改题面、GT、物理阈值、模型或预算。
没有启动付费评测或新的 OpenFOAM 计算，没有覆盖原 Astra / Kimi 运行。
外部 SSH / API 仍可能断线；修复目标是可诊断、有限恢复、不重复执行和不制造成绩，
不是声称网络永远不出错。

**最终验证：1413 passed，0 failed / error，12 skipped，2 deselected。**
源码绑定与所有必过组核对均通过（`core-and-subscription-xhigh`，`missing_required=[]`）。
没有启动新一轮模型成绩评测；这些通过数是工程测试数，不是模型题目得分。

## 原故障与现在的处理

| 场景 | 事实 | 新处理 |
|---|---|---|
| s-203 求解后日志回收失败 | 求解器退出码 0；原日志约 19 MB，结尾 End；最终验收没做 | 退出码仍先落盘。只读传输失败最多尝试 3 次，日志读取使用压缩及独立 120 秒期限；不重新提交求解 |
| SSH 失败被当成“还在运行” | 旧 status 吞掉全部 RuntimeError，外层可无限观察 | 仅确实缺失退出文件才返回 unknown；连接/权限/证据错误继续上报。观察同一作业也有终止窗口 |
| 原生异常只保存类型 | 旧 s-203 只留下 RuntimeError，精确历史原因已丢失 | 保存正文、调用位置及因果异常；私有 incident、SQLite、实时 transcript 均可定位，绝不发给模型 |
| s-204 HTTP 200 后断流 | RemoteProtocolError，流停在工具参数片段，原请求无终态 | 即使读取抛异常也 fsync 已收原文；另记已收字节、最后事件、半截事件大小和本地传输关闭凭据 |
| 断流使已有修改无法恢复 | 旧控制器仍保留上一完整提交的文件，而实际工作区已经改变 | CLI 退出且 broker 结束后捕获失败工作区、原生会话和实际事件，并绑定原始 I/O；它不是有效提交 |
| 未知请求是否自动重发 | 不能知道上游是否继续生成或计费 | 默认仍禁止重发。提供人工显式确认后的“新续接”，原请求永远保留 unknown 与原调用计数 |

本次通过新只读传输路径实际读取 s-203 原有集群证据：

- 原生退出码 **0**，用时 **806.9155 秒**，未超时。
- 完整日志 **19,312,827 字节**（保留首尾空白），最后物理时间 **1.5 秒**，结尾 `End`。
- `new_model_requests=0`，`new_native_runs=0`，`physical_acceptance=not_evaluated`。
- 最终读取凭据：`audits/s203-s204-recovery-20260916-001/real-log-readback-002/readback.json`。
  首轮读取沿用旧 SSH 的 `.strip()`，少保存了末尾 2 字节空白；也已修复并加入字节保真测试。

这证明新读取路径能回收原日志，不证明原 s-203 已通过 GT。旧异常正文没有被保存，
不能倒推出当时一定是哪种 SSH/网络故障，更不能把推测伪装成历史日志。

## 专家看什么

每道题的 `transcript.md` 增加“原生执行／证据回收异常”和“失败工作区”条目。
`scoreboard.md` 展示最近原生异常，以及人工确认续接次数、仍未知的原请求数。
它们与模型数值失败分开。完整证据仍在：

```text
trials/<task>/
  incidents/native-*/error.json        原生异常，正文与调用位置
  native/transport/<op>/reads/<id>/    每一次只读回收的尝试与失败
  turns/<turn>/failure_checkpoint.json 控制器保存的失败检查点
  agent/<workspace>/submission-*/
    failure_checkpoint.json           同一检查点及原始 I/O 哈希
    api/call-*/response.raw            完整或半截原始流，不覆盖
    api/call-*/stream_closed.json      本地关闭≠上游成功/取消
    api/call-*/interrupted.json        错误正文、位置、HTTP 状态
  recoveries/provider-turn-*/          人工确认、前后状态绑定和提交凭据
```

正常完成仍走原提交/执行/评分流程。读日志失败时不改变输入、不增加模型调用，
缓存的退出记录避免重跑已完成命令。原生恢复只处理原来的 run ID。

## 断流后的显式继续

此入口仅适用于**采用新版管线、已写出完整失败检查点的运行**。旧 s-204
缺少这些新凭据，不能直接冒充满足条件；本轮也没有修改它的冻结代码或状态。

以下命令只准备状态，不启动模型或 OpenFOAM。应在该运行原来的冻结源码环境执行：

```bash
python -m agentcfd_bench.provider_recovery \
  --root /absolute/path/to/trial \
  --apply --acknowledge-unknown
```

它检查控制器锁、CLI 退出和进程组消失、broker 流关闭、原始 I/O、原生会话、
当前受评输入与检查点一致，以及任务/协议/预算没有改变。符合条件后保留同一会话，
增加一条不含验收信息的续接通知。**没有重放半截工具或复制上一请求。**

随后由操作者使用该轮原来的单题启动命令，加 `--resume` 与明确的付费授权。
普通 matrix `--resume` 只观察已有记录/推进未启动题，不会替你重测已退出题。
恢复准备可重复调用，但事务间断不会重复增加次数。每题最多两次显式续接，
32/64 等总调用预算均沿用本题原配置，原失败请求不退款式清零。

订阅路径只允许最后一个已关闭的 HTTP 200 响应流中断；更早请求必须有完整、
模型身份正确的结果。保留自定义 API 路径；其已知 `length` 截断可使用相同检查点
机制，未知结果缺少本地关闭证据时仍拒绝继续。鉴权失败、不同模型、损坏证据、
还在运行的进程、watchdog 强制退出等不由这个入口自动处理。

## 代码与永久回归

- `adapters/cluster_native.py:_read/status`：只重试读取，限制次数、保留原因。
- `engine.py:run`：先保存退出/失败证据，恢复时不重复计费或重复累计原生耗时。
- `adapters/native_responses.py:durable_response/Broker`：断流也保存原文和关闭状态。
- `smoke/agent.py:Agent.step`：中断时保存真实工作区/会话，不当成一次有效提交。
- `provider_recovery.py:recovery_state/prepare`：显式确认、原生续接、事务恢复。
- `diagnostics.py:exception_record`：有界、去凭据的异常详情；不捕获局部变量。
- `tests/test_native_recovery.py`：19 MB 原文、瞬时/永久 SSH 错误、退出后崩溃、无重复求解、有限观察。
- `tests/test_provider_recovery.py`：默认阻断、显式续接、预算、证据篡改、进程存活和事务中断。
- `tests/test_transport_incident.py`：真实本地 HTTP 200 截断，保存 RemoteProtocolError 和原始尾部。
- `tests/test_subscription_backend.py`：真实隔离 Codex xHigh 对假 API；执行前一完整工具、拒绝半截工具、原会话继续。

以上核心回归已加入 `ci_checks/release_evidence.py` 的必过组。测试结果另见本轮
`audits/s203-s204-recovery-20260916-001/` 的 JUnit 和执行时源码绑定。
历史资格与旧代码指纹不可用于冒充新版已通过发布检查。

## 回归过程中发现的旧测试问题

完整首轮为 `tests-full-001.xml`：1344 通过、2 失败、79 跳过。
两项失败来自 `test_author_closeout_report` 和 `test_free_mesh_draft`：断言仍要求
旧 `geometry-only-free-mesh-en-v2` / `expert-reference-v1`，但用户已指定移除
`task_contract` 的 `geometry-only-free-mesh-output-v1` / `expert-output-v1`。
本轮更新了这两个测试，继续严格检查四道 20x 题、xHigh、禁用子 Agent 和原预算，
没有放宽评分，也没有修改既有 YAML 来迁就过期测试。

`tests-release-002.xml` 是人工中断的中间测试，不是发布证据：639 通过后暂停，
为了补上未知流的模型身份校验。中断产生的 JUnit 计数不完整，被源码绑定插件拒绝；
没有补签成功记录。所有中间报告保留，最终发布判断只使用之后的完整回归。

## 最终验证与复现

最终报告为 `audits/s203-s204-recovery-20260916-001/tests-release-003.xml`，
同名 `.binding.json` 在测试执行前后绑定源码。耗时 626.72 秒，选中 1425 项：
1413 通过、12 跳过，无失败/错误；另有 2 项旧 Ultra 测试未选入。

12 个跳过项是：4 个旧接受参考的只读大场回放、3 个需指定作者候选目录的回放、
1 个需指定旧 Astra 事故目录的回放、4 个当前接受参考的只读回放。
没有把缺少外部证据的回放补算成通过。真实 Codex xHigh（含 Astra 模型身份）、
Kimi Code、Claude Code、FoamClaw 对本地假 API 的接口/隔离测试均已执行。
唯一警告来自旧温度绘图脚本使用的系统 SciPy/NumPy 版本范围不匹配，相关测试通过；
本轮没有更改该绘图环境，评分/恢复库不依赖 SciPy。

在项目根目录复现无付费测试（JUnit 必须使用一个尚不存在的新路径）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:ci_checks:../.venv-harbor/lib/python3.12/site-packages \
FOAMCLAW_TEST_CODEX_ISOLATION=1 \
/usr/bin/python3 -m pytest -q -p release_pytest --release-root . \
  --junitxml=/absolute/path/to/new-test-report.xml tests ci_checks \
  -k 'not real_subscription_transport_files_isolation_and_resume and not real_ultra_child_calls_are_counted_and_isolated'
```

旧运行的冻结代码和就绪证据没有替换。新一轮正式运行需要用本轮最终证据生成
新的冻结配置/接口就绪记录，不能沿用旧 YAML 所指向的旧源码测试凭据。
本轮未自动执行这个付费启动流程，也未修改当前 Kimi 独立运行。
