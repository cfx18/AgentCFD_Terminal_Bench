# Harness 桥接交付与验证（2026-09-12）

本轮添加正式结构接口和配置 skill，未替换执行框架，未改变题目/评分协议，
未启动模型或集群评测。原始测试报告：`harness-bridge-test-results.xml`。

## 入口

- `agentcfd_bench/adapters/contract.py:Harness/HarnessFactory`：现有依赖注入的正式类型约定。
- `agentcfd_bench/engine.py:run/resume`：接受上述 factory；付费 CLI 仍只路由 Codex。
- `skills/bridge-benchmark-harness/SKILL.md`：可安装的自包含 skill。
- `skills/bridge-benchmark-harness/scripts/configure.py:configure/doctor`：stdlib 配置/检查工具。
- `skills/bridge-benchmark-harness/references/bridges.md`：逐 harness 源码入口与缺口。
- `tests/test_harness_setup.py`：14 项离线配置/接口测试。

安装位置为 `/root/.codex/skills/bridge-benchmark-harness`，与项目 skill 源码核对一致。
新任务中可通过 `$bridge-benchmark-harness` 请求配置。当前任务的技能列表可能
需要新建任务后刷新；安装路径中的脚本可直接执行。

## 实际支持范围

| Harness | 配置生成/静态检查 | 当前独立项目生产桥接 |
|---|---|---|
| Codex CLI | 已测试 | 原有 factory + namespace/broker，需当前资格证据 |
| FoamClaw | 已测试，真实旧源码 AST 检查成功 | 尚未实现隔离 worker/工具与会话转换 |
| Claude Code | 已测试 | 尚未实现原生协议、预算和会话桥接 |
| Kimi Code | 已测试；不自动替换成 Kimi CLI | 尚未实现客户端身份确认与会话桥接 |

生成的 `harness.json` 不是运行就绪证书；`doctor` 为只读静态检查，其 exit 0
不表示可以付费运行。全部新配置均有 `paid_ready=false` 和具体 blocker。
配置包不会被付费 CLI 自动读取，更不会自动触发新客户端安装、登录或评测。
没有把尚未支持的 harness 静默换成 Codex。

## 本轮测试

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:/root/shared-nvme/Caifeixue/AgentCFD/.venv-harbor/lib/python3.12/site-packages \
FOAMCLAW_TEST_CODEX_ISOLATION=1 \
python3 -B -m pytest -q -p no:cacheprovider --junitxml=/tmp/agentcfd-harness-bridge-tests.xml
```

结果：**144 passed，0 failed，0 skipped，35.33 秒**（原有 130 + 新增 14）。
包含真实 Codex CLI、本地假 HTTP API、Linux namespace 与中断/恢复回归。
未测试真实模型质量、真实 provider 新协议、其他客户端安装或本轮真实 OpenFOAM。
skill 的 `quick_validate.py` 校验通过。

实际 FoamClaw 配置包在 `runs/setup-foamclaw-001`：模型明确为 Kimi-K3，保留原
实验预算；该包只是接入准备，不是 FoamClaw 模型成绩。源码只以 AST 解析；
测试特意放入 import 即抛错的模块，验证不会执行导入，也不会导出环境中的密钥。
额外覆盖：旧目录拒绝覆盖、配置篡改、源码修改/增加、符号链接、错误源码根、
doctor 不写文件、自定义类无须继承特定基类。

## 后续正式桥接前必须完成

1. 复用原 ReActEngine，而不是重新写循环冒充 FoamClaw；独立 worker 只加载审阅
   的依赖，文件/运行工具只能访问匿名工作区和统一原生服务。
2. 所有模型请求（含修参和 SDK 重试）在发送层计数；保存原生会话和公开操作记录。
3. 把 harness 版本、源摘要、提示/工具/记忆配置和模型参数绑定到状态与报告。
   本次 setup 指纹尚不等于 scheduler 的恢复身份验证。
4. 完成该 bridge 的假 API 正常/异常/恢复与恶意读路径测试，再做真实运行资格检查。

新增接口文件改变了 `qualification.protocol_identity()` 的代码哈希。
旧资格证据保留，但不能当成当前代码的付费准入；本轮没有为了刷新证书自动申请计算。

Harbor 源码参照：0.22.0 的 `agents/base.py`、`agents/factory.py`、
`agents/installed/kimi_code.py`，以及参照源码中
`tests/unit/agents/test_factory.py` 的自定义 import_path 构造测试。
当前的 dataset adapter、Harbor agent integration 和我们的重复提交接口是三个
不同层次，不能仅靠改类名/命令名互换。
