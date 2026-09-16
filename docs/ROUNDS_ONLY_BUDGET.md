# 轮次预算：rounds-only-v2

新配置：`experiments/science-from-scratch-rounds-v2.json`。
物理题内容及验收未变，所以 task/version 与 science 协议保持原值；预算政策由
独立实验内容和哈希区分，准备报告明确输出 `budget_policy=rounds-only-v2`。

## 什么决定结束

- s-001：累计最多 64 次实际模型 API 请求；改错烟测：32 次、一次最终文件提交。
- 成功即结束；没有模型 token、费用或累计墙钟配额。
- 请求故障/失联仍保留超时保护，未知请求不盲重发；原生求解安全预算不改。
- 进程 watchdog 从剩余请求数与网络超时推导，用于发现失联/卡死，不是累计模型
  用时评分线。触发属于执行异常，不能记成答错。

## 不再强塞 16384

| 路径 | 新行为 |
|---|---|
| Codex Responses broker | 客户端没填 max_output_tokens 就不发送；填了则原样保留 |
| 四 harness 共用 Chat broker | 不添加默认 max_tokens，不裁剪显式较大值；保留 Chat max_completion_tokens 参数类别 |
| Claude Code | 不再注入 CLAUDE_CODE_MAX_OUTPUT_TOKENS |
| Kimi Code | 不再注入 KIMI_MODEL_MAX_OUTPUT_SIZE |
| FoamClaw worker | 不再固定发送 max_tokens=16384 |
| 配置助手 | 默认复制 rounds-v2 实验，不再复制旧额度配置 |

客户端、模型服务仍有各自上下文/输出默认值或硬限制。它们应在原始请求与响应中
记录，不能把移除评测层限制说成“无限输出”。Responses 的该字段是可选的，且涵盖
可见输出和推理；见[官方 API 文档](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)。

旧实验和显式 legacy 配置保持原含义，不能在旧分数上偷偷改变上限。旧可选 ceiling
实现仅用于显式历史配置；新入口不会传入它。烟测代码哈希/客户端身份变更会阻止
旧运行混用，新的付费运行必须重新资格检查。

## 统计，而不是额度

`agentcfd_bench/telemetry.py` 读取已持久化的 provider 终态证据，不重新调用 API。
`AgentTurn.usage` 随提交收据保存；`engine.py` 在同一状态事务内汇总，恢复不重复计数。
API 异常发生时，已经收到的 usage 也会保留。

- input_tokens、output_tokens、total_tokens、reasoning_tokens、cached_input_tokens。
- 每字段有 coverage（多少请求确实报告），不能把部分可见合计当完整总量。
- 推理是输出的一部分，缓存是输入的一部分，不额外重复计入 total。
- output_truncations 单独统计；它不证明题目做错，也不隐含额外重试权限。
- 明确金额和币种的上游 cost 才记录；未提供费用/价格配置时显示未知，不填 0。
- 流式响应只提取一次终态用量，未知/不完整收据不补造 token 消耗。

本次没有改变截断后的整套客户端恢复策略，也没有重新测旧成绩；主要完成预算
移除和统计。客户端/上游自身额度仍可截断，不能仅凭移除评测层上限保证不再发生。

## 回归测试

`tests/test_rounds_only_budget.py` 验证字段省略、较大值不裁剪、调用数终止、超过旧
时间额度仍继续、超大 usage 不触发停止、缺失费用、流式去重及崩溃恢复不重复统计。
`tests/test_harness_smoke.py` 使用四个真实客户端连接本地假 API 验证完整工具和恢复链路。
全套测试不读取真实 API 密钥、不发起付费请求、不申请 OpenFOAM 节点。

2026-09-12 验证：**188 passed，0 failed，0 skipped，77.74 秒**，见
[JUnit 原始结果](rounds-only-test-results-20260912.xml)。另通过无付费完整流程演示及
已安装配置 skill 的静态生成检查。旧实验/成绩未修改，没有启动新付费评测。

四个真实客户端连接假 API 时观察到的请求（不是 provider 的容量承诺）：

| 客户端 | 本次客户端自行发送的额度 |
|---|---|
| Codex 0.153.4 | 未发送 |
| FoamClaw 受控 worker | 未发送 |
| Claude Code 2.1.0 | max_tokens=32000 |
| Kimi Code 0.28.1 | max_tokens=131072 |

这些值未由评测层注入或下调；完整原文与转发请求均有收据，测试逐条核对一致。
