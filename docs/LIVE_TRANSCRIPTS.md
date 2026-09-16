# 运行时自动写入的 I/O transcript

不需要等测试结束，不需要 export 命令，不调用另一个模型整理，也不要求为每条 transcript 算哈希。
新的共享 harness 入口默认启用；Codex 的订阅后端与自定义 API 后端均接入，同一入口下的
FoamClaw、Claude Code、Kimi Code 也接入。旧批次、已经冻结的 runtime 不会自动改变。

每题在宿主 trial 根目录产生：

```text
results/trials/<task>/
  transcript.md               按捕获时间追加的中文阅读版
  transcript.jsonl            同一批事件的结构化原始内容，便于筛选和标注
  transcript-errors.jsonl     只有记录器发生错误时才创建
  agent/.../submission-*/     仍保留原来的逐阶段原始日志
  state.sqlite               调度状态来源，不被 transcript 替代
```

在新时间指纹归档内，以上相对于归档根目录。单题 API/CLI 直接运行时，它们位于指定的 trial `root`。
例如：`tail -F /absolute/archive/results/trials/s-105/transcript.md`。
正常启动后即持续追加，Markdown 预览器是否自动刷新取决于编辑器；`tail -F` 可以直接追踪。

## 在什么时刻记录什么

| 捕获点 | 当时写入的内容 | 不能据此声称什么 |
| --- | --- | --- |
| Harness 启动前 | 实际提示词、剩余调用预算 | 尚未证明上游收到请求 |
| 模型调用前 | 请求 body；自定义 API 另保留适配后的 body | 没有响应时只知道结果待定，不能算成功 |
| 上游返回时 | 自定义 API 的完整回复；订阅流的每个完整 SSE 事件和结束时残片 | 其中的工具建议不等于已经执行 |
| 客户端 stdout/stderr 到达时 | 原始文件立即写入；每个完整输出行追加到 transcript，EOF 保留残行 | 不把 stderr 本身判为任务失败 |
| 文档查询发生时 | 实际端点、搜索关键词或文档 ID、返回内容、交付状态 | 返回资料不等于模型已阅读或采用 |
| Harness 提交时 | 捕获到的文件内容、提交状态和本阶段调用数 | 不等于验收通过 |
| 独立执行器返回时 | 实际收集到的执行结果、日志与产物 | 不承诺远端尚未传回的求解器日志也实时可见 |
| 产生验收结果/公开反馈时 | 专家侧验收结果；另列将要发给模型的公开反馈 | 私有结果不因记录而额外传给 Agent |

模型公开输出的决策说明、检索前后的理由会原样保留；若它没有说明“采纳了哪条知识”，
这里不会补造。不会获取供应商未返回的内部思考，也不会把 opaque/encrypted reasoning 当成可读思考。
CLI 只在完成一行/事件时才输出的内容，记录器不能提前得到；尚未组成完整行的原始字节已保留在原日志。

同一交互会有上游和客户端两层记录，这是刻意保留的证据，不是两次模型调用。
用 `source` 中的 submission/call 或客户端自己的 tool/item ID 关联；调用数量仍以原预算记账为准。
原始 HTTP 认证头不进入 transcript，已知密钥和敏感认证字段脱敏。不要把密钥写进题面、YAML 或命令。

## 中断、恢复与写入故障

每条记录立即追加并 flush/fsync；多线程及不同 writer 实例通过文件锁串行写入。
JSONL 和 Markdown 是两个文件，不声称二者具备跨文件原子提交。
记录失败时保留已写内容，在 `transcript-errors.jsonl` 和控制器 stderr 报警；不把记录器故障变成模型答案错误。
记录文件不是原子数据库，进程被强杀或磁盘写入中断可能留下尾部残行，不能因此宣称记录完整。

显式恢复时继续追加原文件，不清空、不重放历史请求，不凭缺少回复补造成功。
调度、未知请求锁止、恢复资格仍由原状态库和审计凭据决定。
`report/status` 不生成或补写 transcript。源码更新后不能绕过冻结协议身份门禁直接恢复旧版本运行。

原有 NativeJournal 的哈希继续用于审计证据校验；它与新增的无强制哈希 transcript 是不同职责。
全部 transcript 位于宿主，不挂载进匿名 Agent 工作区；验收结果不会成为被测模型的额外提示。

## 代码与免费验证

- [live_transcript.py](../agentcfd_bench/live_transcript.py)：追加写入、中文标题、stdout/stderr 实时分流和 SSE 观察。
- [共享 Agent](../agentcfd_bench/smoke/agent.py)：提示词、四种 harness 的进程输出及提交；不另造 Agent 循环。
- [自定义 API](../agentcfd_bench/smoke/broker.py)、[订阅流](../agentcfd_bench/adapters/native_responses.py)：在收到回复时记录，先于格式验收/转交。
- [文档入口](../agentcfd_bench/documentation.py)、[交付](../agentcfd_bench/documentation_service.py)：实际查询与返回，而非从模型话术推断检索。
- [调度器](../agentcfd_bench/engine.py)：运行结果、评分和将要发给 Agent 的反馈，分别标记。
- [测试](../tests/test_live_transcript.py)：子进程仍等待时记录已可读；四桥接入口；流拆包；格式拒绝前保存；中断残片；追加恢复；并发；密钥隔离；假执行器验收。

这些测试使用假 API、假进程或假执行器；不是新模型成绩，也不等于订阅传输问题已全部修复。
本次不启动付费评测、不运行 OpenFOAM、不绕过现有发布阻断。

2026-09-15 验证记录：

- [全常规回归](../audits/live-transcript-full-20260915-tests-003.xml)：917 passed，62 项显式 opt-in 客户端集成跳过，0 failed。
- [四种真实客户端补测](../audits/live-transcript-real-clients-20260915-tests-004.xml)：4 passed；Codex、FoamClaw、Claude Code、Kimi Code 均对接本地假 API，覆盖工具写文件、隔离和三阶段会话恢复。补跑了上述跳过项中的 4 项，其余 58 项未补跑。
- [最终实时记录专项](../audits/live-transcript-final-20260915-tests-005.xml)：15 passed；包括最后的中文阅读版/流事件折叠显示修改。
- [归档与配置专项](../audits/live-transcript-archive-20260915-tests-002.xml)：95 passed，与前述回归有重叠，不相加为独立测试数。
