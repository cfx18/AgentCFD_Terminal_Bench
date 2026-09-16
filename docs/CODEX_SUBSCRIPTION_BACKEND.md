# Codex 订阅与自定义 API：两条独立后端

原来的自定义 API 路径仍是默认值；旧实验、`.env` 和历史结果没有迁移或覆盖。
新路径使用本机 ChatGPT 订阅凭据，由宿主添加认证，目标固定为官方 Codex Responses 端点。
不把登录文件复制到被测 Agent，不执行 Responses→Chat→Responses 转换。

```text
实验配置 → 原版 Codex CLI（匿名沙箱）
                 ├─ custom-api → 原 Chat 转换桥 → 用户的 API
                 └─ chatgpt-subscription → 原生 SSE 转发 → 官方 Codex
                                             ↑
                                      宿主认证／累计请求计数
提交文件 → 原有独立 OpenFOAM 服务 → 原有物理验收器
```

## 配置与边界

五题清单：`experiments/sol-ultra-five-v1.json`。每题配置在同目录。

```json
{
  "model": {"name": "gpt-5.6-sol", "wire_api": "responses"},
  "harness": {
    "backend": "chatgpt-subscription",
    "reasoning_effort": "ultra",
    "public_decision_log": true
  }
}
```

这是实验配置的相关片段，不是完整配置。旧配置不增加 `harness` 字段即可沿用自定义 API。
订阅命令不能同时传 `--env-file`；API 命令不能传 `--auth-home`，防止意外切换计费路径。

- CLI 0.153.4 实测把 ultra 映射为底层 `max`＋自动委派。这是 CLI 原生行为，不是适配器降低档位。
- 子任务继承匿名沙箱，所有请求经过同一计数器，累计受每题 64 次模型请求约束。
- 没有 benchmark 添加的单次输出 token 上限；输入、输出和用时是统计量。
- 底层 Responses 请求体、流式输出原样保留；不删除空消息、不重排工具历史。
- 网络连接最多等待 15 秒；收到连接后的响应读取安全超时沿用请求配置。不是模型输出预算。
- 宿主可使用已经配置的本地 CONNECT 代理；它不等于模型中转服务。仅允许 loopback 地址，TLS 校验保持开启。
- Agent 无外网，只能查原来的固定 OpenFOAM 文档库；文档条件不因模型切换改变。
- 新增简短中文公开决策日志：查询目标、关键词、实际使用的返回知识及后续操作。不是完整隐藏思维链，也不是新评分标准。
- 未知请求不自动重放；接口异常和模型解题失败分开保存。

## 代码入口

|职责|文件|
|---|---|
|配置选择与就绪检查|`ci_checks/run_codex_science.py`|
|真实 Codex 命令、工作目录、历史恢复|`agentcfd_bench/smoke/agent.py`|
|宿主订阅认证、官方认证刷新、本地代理限制|`agentcfd_bench/adapters/subscription_auth.py`|
|原生 SSE、累计请求预算、不可覆盖证据|`agentcfd_bench/adapters/native_responses.py`|
|旧自定义 API 桥，保留|`agentcfd_bench/smoke/broker.py`、`protocol.py`|
|独立串行矩阵与实时中文表格|`ci_checks/run_science_matrix.py`|
|保留虚拟环境解释器、检查宿主依赖、后台启动|`ci_checks/launch_science_matrix.py`|
|冻结运行代码，不复制成绩或账号文件|`ci_checks/freeze_science_runtime.py`|

## 运行

在独立项目目录下设置 Python 导入路径后运行。以下命令中的路径必须按实际新运行目录填写；不允许复用旧 Fable 目录。

```bash
python ci_checks/probe_codex_client.py \
  --experiment experiments/sol-ultra-s-105-v1.json \
  --root runs/<新烟测目录> --auth-home /root/.codex --allow-paid

python ci_checks/run_science_matrix.py \
  --project <冻结项目绝对路径> --source-project <原项目绝对路径> \
  --manifest <冻结项目绝对路径>/experiments/sol-ultra-five-v1.json \
  --root <新矩阵绝对路径> --probe <通过的烟测目录> \
  --auth-home /root/.codex --allow-paid
```

接口烟测通过以后，各题仍需新版本的原生正负对照就绪检查。原始参考的已验证输出按哈希导入，不重复完整参考求解。
矩阵运行期间维护 `scoreboard.md` 和 `scoreboard.json`。每题的原始工具轨迹、请求、响应和验收证据保留在 `trials/`。

免费测试重点见 `tests/test_subscription_backend.py`、`tests/test_science_codex_integration.py`。
真实客户端／假 API 测试需要 `FOAMCLAW_TEST_CODEX_ISOLATION=1` 和允许本地 socket、namespace 的宿主执行权限。

## 本轮执行证据（2026-09-15）

- 最终完整回归：两组分别 532、355 项通过，合计 887 项，0 失败、0 跳过。
- 启动器专项另跑 11 项通过（含与全量回归重叠的测试，不另宣称 898 项独立测试）。
- 真实订阅烟测 `sol-subscription-client-probe-003`：5 次请求、5 次完整返回、0 截断；1 次文档搜索、1 次阅读。
- 服务端实际返回模型为 `gpt-5.6-sol`；CLI 配置 ultra，底层请求为 max；请求未添加输出 token 上限。
- 正式目录：`runs/sol-ultra-five-002`；启动日志：`runs/sol-ultra-launch-002/controller.log`。
- 首次矩阵 `sol-ultra-five-001` 的系统 Python 缺少 `harbor`，五题均在原生服务构造时退出，0 次正式模型请求。该记录保留，不能作为模型 0/5。
- 修复方式：后台启动保持 `.venv-harbor/bin/python` 的符号链接路径；启动前用同一解释器构造全部任务的服务对象，验证依赖但不派发作业。测试覆盖这一错误。
- 首次连接烟测和 6 轮预算烟测也保留为接口诊断，不并入模型成绩。
