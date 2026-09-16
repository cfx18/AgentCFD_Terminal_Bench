# 迁移边界与工程参照

参照：harbor-framework/terminal-bench-science 的任务包组织、独立验收和任务清单。
执行依赖固定 Harbor 0.22.0；不复制整题删除重跑机制。Task layout 与 Harbor
接近，但 dataset 的本地 id/content-digest 和循环原生提交是本项目协议，不把
它们伪装成 Harbor 原生的 registry digest 或 CLI 支持。

## 保留

- 现有 Codex CLI/Responses/Chat 适配、原始请求和工具调用证据。
- 匿名工作区、凭据 broker、禁止模型访问参考与验收代码。
- 独立的 OpenFOAM/Slurm/Apptainer 服务；日志清理和运行身份核对。
- 模型输出预算、调用总预算、原生累计预算、不明请求禁止盲重发。
- s-001 题面、参考配置、物理容差及同一会话内提交/后处理协议。

## 修复

1. service 正常返回 error 也写 infrastructure_error；不会再继续消耗模型预算。
2. request.json 存在而 agent_started 未提交时，核对相同请求再登记；不覆盖证据。
3. SIGINT/SIGTERM 写 interrupted，重复取消不破坏清理；本次 CLI 子进程组受控结束。
4. 运行状态冻结 task_digest，不能在恢复时偷偷切换题目内容。

## 未混入本轮

旧八百多道改错题、DPSK judge、旧任务控制器与历史结果仍在原项目。当前独立
项目只发布一题，不制造 r-001 占位题或擅自改变题库分母。新增另一任务线需另行
迁移和审核；本轮没有启动模型评测。

## 单任务的可审阅边界

- instruction.md：模型到底看到了什么。
- environment/report-schema.json：需要后处理哪些量、单位和长度。
- tests/acceptance.py：公开约束检查、实际字段独立提取、报告真实性和定量误差。
- solution/reference.py：参考输入，不作为模型的初始工作区。
- authoring/REVIEW.md：物理审核与工程迁移的边界。
- task.toml：运行配方、OpenFOAM runtime identity、资源和隔离政策。

任务目录不进入 Agent namespace。原生输出来自受控服务而非模型自造日志。
任务代码只由验收方加载，模型写出的 Python/Allrun 不在验收环境直接执行。

## 验证入口

`python -m ci_checks.check_tasks` 是静态 release gate；`python -m pytest` 是
框架测试。`prepare --qualify-native` 是实际求解器正负对照，和模型评分分开。
只有显式 `run --allow-paid` 且资格有效才会进入模型评测。
