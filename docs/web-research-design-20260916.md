# 联网重测：接口和实验边界

用户要求停止当前离线轮，并把 s-203（分岔流）与 s-204（自然对流）作为两项独立后台任务并行重测。
保留 Astra xHigh、实验订阅账号、每题 120 次模型调用、无限原生用时和原 GT／评分口径。

## 为什么此前没有网页工具

旧 YAML 为 `network: disabled`；CLI 设置 `web_search=disabled`，宿主仅开放模型回复路由。
本轮真实 CLI 的假服务测试进一步发现：Astra 的 Responses Lite 不使用顶层 hosted `web_search`，
而是原生 `web.run` 加独立 `POST alpha/search`。所以只改 `web_search=live` 仍没有可调用网页工具。
测试先复现这个问题，再通过声明 `supports_standalone_web_search=true` 和固定搜索路由解决。
没有改模型元数据中的 Responses Lite 模式，也没有替换模型。

上游实现参照：[搜索客户端](https://github.com/openai/codex/blob/main/codex-rs/codex-api/src/endpoint/search.rs)、
[工具执行](https://github.com/openai/codex/blob/main/codex-rs/ext/web-search/src/tool.rs)、
[自定义供应商能力测试](https://github.com/openai/codex/blob/main/codex-rs/core/tests/suite/responses_lite.rs)。
本地实际验证使用已安装 Codex CLI 0.153.4，而非仅依据主分支源码推定兼容。

## 代码边界

| 入口 | 职责 |
|---|---|
| `harnesses/research.py` | 明确的资料访问条件和公开查询记录要求 |
| `harnesses/codex.py` | CLI 能力开关；shell 的独立网络命名空间不变 |
| `harnesses/_transport/adapters/web_research.py` | 仅固定官方 `alpha/search` 路由；宿主加认证；不追随跳转、不自动重试 |
| `records/transcript.py` | 实时保存请求、返回资料和异常；不补造内部推理 |
| `reports/summary.py` | 标明联网／离线实验条件 |

宿主网络不直接开放给 shell 或 OpenFOAM。工作环境仍只有自己的公开题目、工作文件、离线文档及自身结果。
网页查询在官方服务端执行；代理不是任意目标 HTTP 转发器。凭据不进入 Agent 环境、配置快照或 transcript。
搜索是工具操作，单独登记，不另占模型生成次数；其原生返回长度参数保持不变，不新增模型 token 上限。
上游搜索失败也保留 HTTP 状态和真实响应；未知结果不伪造成功、不自动重放。

## 审阅与解释

`trials/<task>/transcript.md` 中的“联网查询请求”和“联网查询／阅读”分别是实际搜索条件与服务端返回。
原始收据在 `calls/turn-*/api/web/*/`。Agent 的公开研究笔记单独保留，说明哪些资料影响了决定。
拿到资料不等于正确理解；如上游没有返回完整页面，不凭空补齐。
公开论文、官方文档和教程均可查，因此结果应标记 open-web / reference-assisted，不能冒称闭卷泛化。

两份单题配置为 `experiments/dense-reconstruction-astra-web-120-s203.yaml` 和 `...-s204.yaml`。
分别用 `python -m agentcfd_bench.launch <配置> --allow-paid` 启动；控制器脱离终端，冻结配置与代码。
每题有自己的 UTC 指纹目录，输出根目录 `runs/dense-reconstruction-web/`。

本地测试覆盖真实 CLI 发起搜索、知识返回下一轮、同会话续接、私有目录不可读、无 shell 外网、
禁用时拒绝搜索、错误模型拒绝、HTTP 错误原样保存、凭据不泄漏和超时不重发。
测试结果见同目录 `web-research-local-tests-20260916.xml` 与 `web-research-full-tests-20260916.xml`；
这些是无付费的接口／工程测试，不等于真实模型已经解题成功。
