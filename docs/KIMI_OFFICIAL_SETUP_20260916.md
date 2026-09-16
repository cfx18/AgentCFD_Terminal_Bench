# Kimi 官方 API 切换：官方接口和发布回归通过

## 已停止的旧运行

用户要求停止 Kimi 中转 API，改用其充值的 Moonshot 开放平台。
旧轮次 `runs/manual/kimi-code-k3-output-20260915T163225245735Z-4fd30c18bf86-8f56d4bc`
的控制器及子进程已退出；`results/campaign/s-203-exit.json` 记录
`interrupted: true, returncode: -9`。没有删除历史记录，也没有改写成绩。
旧 YAML 的 `release.ready` 已关闭。Astra 控制器及冻结源码不改动。

## 用户配置位置

编辑独立的 `.env.kimi-official`，只填写 `SCIENCE_API_KEY`。
大陆开放平台默认地址为 `https://api.moonshot.cn/v1`；如果账号是在国际站创建，
改为对应的 `https://api.moonshot.ai/v1`，使用同站点生成的密钥。
不要把密钥贴在聊天、YAML 或审阅文档中。此文件已受 `.env.*` 忽略规则保护，
权限为仅所有者读写；不会读取旧项目 `.env` 作为回退。

官方文档中的模型 ID 是小写 `kimi-k3`，不是旧中转别名 `Kimi-K3`：
[官方快速开始](https://platform.kimi.com/docs/get-api-key)。
已用用户账号查询官方 `/models`：HTTP 200，列表包含 `kimi-k3`。
记录位于 `audits/kimi-official-20260916-001/models-check.json`；仅查列表不计作模型调用。

新 YAML 为 `experiments/science-kimi-official.yaml`；任务、预算、文档、GT
保持原四题条件。仅为 Kimi Code 和既有通用 Codex 桥接允许显式 `kimi-k3`，
不顺便启用其他模型或改变模型排除名单。保留旧自定义 API 路径，但不用于本轮。

## 传输修复与边界

- 仅 Kimi 的本地 HTTP fetch 改用 Node `http`，避开 Undici 自身的响应头期限；
  保留 SDK AbortSignal、600 秒请求 watchdog，不无限等待，不生成假的提前响应。
- 把 SDK retry 标记透传至宿主；重试和未确认交付的同一请求在宿主拒绝，
  不再次调用官方 API，不把重试伪装成新的 Agent 决策。
- 分别记录 broker→relay、relay→client 交付结果；保存完整上游响应后才交付。
  socket 写入完成仍不等于客户端已消费，收据继续保留 `client_received: unknown`。
- 修复 Chat→SSE 转换遗漏 `reasoning_content` 和 usage 的问题。
  本地真实客户端测试证明 returned reasoning 可被接收、保存并在后续工具结果请求回传。
  这不等于捕获模型全部隐藏思维。
- 请求结果未知或交付失败时，控制器一题即暂停后续派发，保留证据等待处理。
  物理答错不触发基础设施暂停；不修改 grader。

## 真实官方接口烟测

`audits/kimi-official-20260916-001/client-probe/result.json`：通过，
4 次请求 / 4 个已知响应，全部 HTTP 200，实际返回 `kimi-k3`。
每次用时约 11.52、9.55、6.51、7.53 秒。完成文档搜索 1 次、正文 read 0 次，
写入并通过 JSON 解析读回接口测试文件。无 OpenFOAM 提交、无物理评分。
输出截断 0；输入 87659 token、输出 476 token（含 reported reasoning 86）、
缓存输入 65536；API 未报告费用，不把费用记为零。

仍使用已安装的 Node Kimi Code 0.28.1 的 OpenAI-compatible provider，
不是更换成 Python Kimi CLI，也不是另造 Agent 循环。上下文配置仍为 131072。
第一请求 `max_tokens=131072`、后续随上下文减少，均来自客户端自身，宿主不注入输出上限。
既有 fixed-chat 协议不转发额外的 reasoning_effort：该旧客户端在出现 reasoning
历史后会自动提出 `medium`，但官方 K3 支持 low/high/max、默认 max。
本轮请求未发送该参数，保持官方默认；请求／转换后请求均保存供审阅。
因此新旧轮次除了提供方，也有 reasoning 历史交付修复，不能归因为纯提供方对比。

## 发布证据与运行边界

新配置已通过就绪前的证据核对，`release.ready: true`；不复用旧提供方的接口证据。
最终发布回归 **376 passed、1 skipped、4 deselected，0 failed / 0 error**，
451.69 秒。跳过的是未指定旧数据路径的历史 Astra 事故回放；未选入的四项是
未改动的参考数值回放。实际客户端测试、隔离、恢复、传输防重试、预算和
必须通过的发布门槛均已执行。
`audits/kimi-official-20260916-001/tests-release.xml` 和同名 `.binding.json`
在测试执行时保存运行前后源码绑定；只读 `release_evidence.verify` 返回 passed。
通过后在独立新目录提交四题。短接口烟测不等于长任务没有超时风险。
单次请求若超过 600 秒，仍应明确记录基础设施异常而非模型答错。

本次无付费配置回归：`ci_checks/test_probe_client.py`、
`ci_checks/test_campaign_config.py`、`tests/test_harness_identity_binding.py`，
共 **87 passed / 0 failed**（39.05 秒）。证据为
`audits/kimi-official-20260916-001/tests-configuration.xml`。
这些覆盖模型原名传递、独立凭据入口、就绪阻断和配置一致性，
不代表真实官方 API、长响应传输或 OpenFOAM 已验证通过。

随后传输定向回归 44 passed；包含完整字段回传与真实客户端的回归 28 passed。
报告分别为 `tests-transport-001.xml` 和 `tests-transport-002.xml`，
均位于本次 audit 目录。它们不替代最终的源码绑定发布证据。

## 已启动的独立正式轮次

归档：`runs/manual/kimi-official-20260915T173538765035Z-6e1db76f9da5-6a99c9a0`。
使用 UTC 时间指纹；本记录文件名沿用本地日期。
静态就绪检查 `ready: true`、blockers 为空；独立 matrix PID 1269484，
首题子进程 PID 1269504。s-205 的既有 GT 证据校验通过后开始正式模型请求。
校验通过、进程存活和模型响应都不计为物理题通过。

- [实时成绩](../runs/manual/kimi-official-20260915T173538765035Z-6e1db76f9da5-6a99c9a0/results/scoreboard.md)
- [s-205 实时 I/O](../runs/manual/kimi-official-20260915T173538765035Z-6e1db76f9da5-6a99c9a0/results/trials/s-205/transcript.md)
- [控制器日志](../runs/manual/kimi-official-20260915T173538765035Z-6e1db76f9da5-6a99c9a0/launch/controller.log)

无需 Agent 持续监控。控制器独立执行并更新文件，可从项目目录运行：

```bash
bash ci_checks/science.sh status --run-dir runs/manual/kimi-official-20260915T173538765035Z-6e1db76f9da5-6a99c9a0
tail -F runs/manual/kimi-official-20260915T173538765035Z-6e1db76f9da5-6a99c9a0/results/trials/s-205/transcript.md
```

不要再次 submit 来“恢复”此轮；再次提交会创建并收费运行新的独立实验。
