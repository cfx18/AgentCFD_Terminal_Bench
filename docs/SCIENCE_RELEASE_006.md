# Build-006 正式部署记录

2026-09-13，matrix-002 全部终止后部署；**没有启动新的付费批次**。

**本轮发布门禁已完成**：[最终就绪凭据](../runs/deployed-build-006-001/ready.json)。
这限定于已审阅的五题、四 harness 配置；不保证任意新题、外部 API 或存储永不失败。

- 已部署：16 个代码文件、4 个新增测试文件、1 个旧测试文件的两项 HTTP 状态断言。
- 部署字节与候选完全一致；任务、原始参考、数值阈值、文档和模型配置未改。
- 旧文件保存在 `runs/deployed-build-006-001/before/`，不覆盖历史实验。
- 候选副本测试：758 passed、0 failed、0 skipped。
- **部署后测试：758 passed，0 failed，0 skipped，484.18 秒**；实际客户端本地假 API
  测试全部开启。源码与候选一致、运行中未变，无付费/原生执行或外部动作拒绝记录。
- **新原生资格：全部通过**，五题 30 项标准门禁及 3 项显式默认系数对照通过，
  使用 `tutorial-science-qualification-003`，不是沿用旧资格。18 个作业的完整凭据
  已重放，资源释放已核验，均已不在队列。

证据：[部署计划](../runs/deployed-build-006-001/plan.json)、
[逐字节核验](../runs/deployed-build-006-001/deployment.json)。
完整测试：[summary](../runs/deployed-build-006-001/tests-001/summary.json)、
[JUnit](../runs/deployed-build-006-001/tests-001/junit.xml)。原生驱动另有 6 项无执行测试
通过，含逐系数变值拒绝、缺失/重复日志块、未知操作观察与截止；
[单列记录](../runs/deployed-build-006-001/driver-tests-001/summary.json)，不混算成 764 项完整回归。

原生结果：[可读资格表](../runs/tutorial-science-qualification-003/report.md)、
[原始汇总](../runs/tutorial-science-qualification-003/result.json)。三项显式默认系数
对照的最终场均与原参考完全一致。全部 18 个新算例共执行 54 条原生命令，
累计命令时间 216.43 秒，不含调度、传输和审计等待；原始参考重跑和付费模型调用均为 0。

按 bridge-benchmark-harness 技能要求，接口验证运行了四个真实客户端，检查身份、
隔离和恢复，不以纯 mock 冒充客户端适配完成。测试后的 98 个记录 PID 均不存在，
其中含测试夹具 PID，不宣称是 98 次真实客户端启动或穷尽所有后代进程。

## 修了什么

| 边界 | 正式代码 | 效果 |
|---|---|---|
| v2306 配置等价 | `foam/science_contract.py`、`foam/default_coefficients.py` | 支持 model 别名、latestTime 和显式不变默认系数；不放宽物理值 |
| 工作目录与提交 | `submission_contract.py`、`smoke/agent.py`、`engine.py` | 明确 /work 根部与新鲜 action；不代写、不搜索合并子目录 |
| 文档服务 | `documentation_service.py`、两个 broker、docs_client | 文档独立处理，不排在长模型请求后面 |
| 文档统计 | `documentation_statistics.py`、`telemetry.py`、`reporting.py` | 区分生成、传输状态；不声称模型实际读到 |
| 上游结果与恢复 | `provider_outcome.py`、`engine.py`、适配器 | 已知截断/已知执行失败与未知请求分开；不重发、不重复计数 |
| 本地失败退避 | `smoke/broker.py` | 锁止后返回非重试 400，保留真实上游状态和凭据 |
| 身份绑定 | `smoke/agent.py:harness_identity`、`science_campaign.py` | factory、实例、调度器共用身份；旧会话拒绝新代码 |

上述源码路径相对于 `agentcfd_bench/`。公共多 harness broker 的失败锁止修复
不代表旧单任务 Codex broker 的所有失败策略都已统一。
没有增加单次输出 token 上限，没有改成另一套冒名的客户端推理循环。
这些修复不解决 Ceph 或上游服务本身的故障。

## 验证入口

```bash
# 正式源码完整测试：真实客户端仅连接本地假 API，无付费/原生运行。
.venv-harbor/bin/python -B AgentCFD_Terminal_Bench/ci_checks/check_deployed_release.py \
  --candidate AgentCFD_Terminal_Bench/review_candidates/integrated_release_v1/build-006/project \
  --closure AgentCFD_Terminal_Bench/runs/tutorial-science-matrix-002/review/closure-002 \
  --campaign AgentCFD_Terminal_Bench/runs/tutorial-science-matrix-002 \
  --output AgentCFD_Terminal_Bench/runs/deployed-build-006-001/tests-NNN
```

从父项目目录执行，测试目录必须新建。完整测试包含身份、隔离、预算、异常与恢复。
发布后原生门禁使用 `ci_checks/qualify_deployed_release.py`，必须显式 `--execute-native`。
它只复用原始正例并执行预登记控制；不读取 API 密钥或调用模型。

已执行原生计划：五题各三项新控制（缺输入、错误物理、合理数值变化），另三项
显式默认 kEpsilon 系数对照。共 18 个新原生算例，原始参考重跑为 0。
原生证据与模型报告严格分离，资格检查产生的测量绝不记为模型提交。

本批终局表见[Matrix-002 审阅](SCIENCE_MATRIX_002_FINAL_REVIEW.md)。
