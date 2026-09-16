# Fable 四道新增题：实现与审阅入口

2026-09-14。首题 s-105 的原试验保留，新增四题分别为 s-202 至 s-205。
不是重跑首题、不是改错题、没有调用其他付费模型。

实时五题表：`runs/fable-edge-five-report-001/summary.md`；JSON 同目录。
独立控制器日志：`runs/fable-edge-setup-001/four-task-controller.log`。
每题完整运行：`runs/fable-edge-live-002/trials/<task>/`。

## 此轮实际验收范围

从空匿名目录生成配置，固定只读 OpenFOAM 文档可查，公网未开放。
每题 64 次模型请求；单次原生运行 300 秒，累计原生运行 1800 秒。
没有新加单次输出 token、累计 token 或费用上限。首题沿用原来更短的原生预算，
没有为了统一表格改写其历史实验配置。

公开参数表固定几何、网格排序、材料、边界与活动方程。
数值算法与线性求解器设置不做完整文件相等比较。
模型提交后独立运行 OpenFOAM，验收器重新读取真实的末步全场，与隐蔽原版数值场比较，
并核对模型报告的单位、统计量与残差。热问题的温度误差按温升尺度归一化，
不拿 300 K 的绝对温度掩盖温升错误。

这仍是固定离散与有限时长的数值复现试验；**不宣称完成独立界面热流、总能量守恒、
网格无关性或实验数据验收**。s-204 原版跑到 1000 次迭代时并未达到全部提前收敛阈值，
所以它的参考是实际 1000 次迭代状态，不应被称为完全收敛的稳态真解。
仅物理契约检查失败或数值差异超限，不能未经轨迹审阅直接归因为“物理理解错误”。

## 源数据与准备发现

源归档 SHA256：`d7fba773658c0f06ad17f90199565f32e9bf502b7bb03077503642064e1f5344`。
`edge_sources.py` 在归档内部解析有限的案例内软链接，拒绝逃逸、循环和非普通文件。
14 份原版多区域软链接曾被旧快照遗漏，此轮恢复为原归档内容，没有重写物理设置。
按原 Allrun 的 restore0Dir 将 0.orig 激活成 0，原脚本和映射都保留为私有来源证据。

| 任务 | 原版输入文件 | 完整原版原生秒数 | 使用的参考证据 |
|---|---:|---:|---|
| s-202 | 47 | 57.239 | `runs/fable-edge-originals-002/s-202/` |
| s-203 | 13 | 13.002 | `runs/fable-edge-originals-001/s-203/` |
| s-204 | 17 | 206.106 | `runs/fable-edge-originals-002/s-204/` |
| s-205 | 10 | 1.542 | `runs/fable-edge-originals-001/s-205/` |

以上都是作者原版参考，不是 Fable 的成绩。
最初 s-202/s-204 的失败是固定镜像缺少 4 个程序；新建 v4 镜像，旧 v3 不变。
v4 SHA256：`1b8daf015bedab9fc337a623e8516c81f805d69a53a6e58436c46fb3053b5bd1`。
多区域求解正常退出后，原生日志超过旧读取器的 4 MiB 限制。现按运行器已有的 32 MiB
单文件限制完整读取，未截断末步证据，也未重跑求解器；回收修复有独立凭据。

## 代码职责

| 内容 | 文件 / 函数 |
|---|---|
| 原版归档与软链接审计 | `agentcfd_bench/edge_sources.py::case_files/export` |
| 原版执行，不调用模型 | `agentcfd_bench/edge_tasks.py::OriginalTask/prepare_original` |
| 固定原生配方 | `agentcfd_bench/execution_spec.py::EDGE_RECIPES/ExecutionSpec` |
| 独立执行与已退出命令恢复 | `agentcfd_bench/runtime.py::NativeService.execute/cluster_service` |
| 材料、方程、局部 include 的安全边界 | `agentcfd_bench/foam/edge_inputs.py::validate/trees` |
| 物理约束、字段单位、末步提取、评分 | `agentcfd_bench/edge_acceptance.py::EdgeAcceptance/snapshot` |
| 原版执行证据导入，不重绑原任务身份 | `agentcfd_bench/edge_baseline.py::audit/import_identity` |
| 题面、报告模板、对照构造 | `agentcfd_bench/edge_packages.py::stage/controls/alternative` |
| 原生正负对照与付费门禁 | `agentcfd_bench/qualification.py::qualify/require_qualified` |
| 顺序推进四题 | `ci_checks/run_fable_edge_campaign.py` |
| 实际 Codex/Fable 单题执行 | `ci_checks/run_codex_science.py` |
| 免费完整测试通过后才启动 | `ci_checks/after_test_gate.py` |
| 独立只读五题统计 | `ci_checks/report_fable_edge.py` |

运行代码固定在 `runs/fable-edge-runtime-002/`，不在模型答题时改评分器。
s-202 尚未发起模型调用时，其“收紧全部线性容差十倍”的作者替代数值对照超过
300 秒原生预算，原失败凭据保留。为检验合理数值变体是否仍可验收，另建
`runs/fable-edge-runtime-003/`：只把该对照改为 topAir 的 p_rgh 容差
1e-7 → 5e-8；题目、参考、模型预算和评分阈值未变。
新资格检查在 `runs/fable-edge-qualification-003/s-202/`，通过后才允许首次付费调用。
该新资格检查最终六项全部通过，替代数值对照原生耗时 57.304 秒。
每题实验配置是 `experiments/fable-edge-s-20N-v1.json`。
每题原生资格目录是 `runs/fable-edge-qualification-002/<task>/`。
原版参考只导入一次；缺字段、错误物理、合理数值调整各有独立原生对照，另检验伪造报告。

## 免费回归记录

首轮完整回归：827 passed，0 failed，0 skipped，507.05 秒。
JUnit：`runs/fable-edge-setup-001/edge-regression-001.xml`。
调整上述作者对照后，第二轮完整回归：828 passed，0 failed，0 skipped，508.48 秒。
JUnit：`runs/fable-edge-setup-001/edge-regression-002.xml`。
新增针对性测试：`tests/test_edge_acceptance.py`、`tests/test_edge_workflows.py`，现为 39 项。
包含多区域路径、Pa 与运动压力区别、末步字段、零残差、温升归一化、报告造假、
本地 include、宏作用域、动态执行拒绝、链接逃逸和完整大日志回收。

原始请求、工具动作和模型可见的 reasoning 按实际返回保存；
不声称中转站提供了完整隐藏思维链，也不能独立认证中转站背后的模型权重。

## 已知 API 截断与恢复边界

s-203、s-204 的部分 HTTP 200 响应返回 `finish_reason=length`，
completion_tokens 恰为 4096，且没有可执行的工具调用或文本。
已检查发送到网关的 `wire_request.json`：没有 `max_tokens`、
`max_completion_tokens` 或 `max_output_tokens`。
因此这不是此轮新加的 benchmark 输出上限；但现有证据不能区分是网关默认值
还是它所用上游的限制。不得将这些响应算作模型物理答错。

`ci_checks/recover_known_truncation.py` 只对已经收到终态且客户端退出的截断响应
准备续接；未知请求、超时、身份变化、账目不一致和不安全文件均拒绝。
续接沿用原 Codex 会话、文件及累计 64 次调用预算，单独记录每次恢复，
不执行截断内容中的工具，不伪装成首次请求。相同条件最多两次续接；
仍失败则需修复生成窗口，不能无限原样请求。
相关免费恢复测试：`ci_checks/test_known_truncation.py`，13 项通过。
只读延后状态展示测试：`ci_checks/test_edge_live_report.py`，3 项通过。

独立续接日志：`runs/fable-edge-setup-001/known-continuations.log`。
s-202 延后资格检查与首次模型测试：`runs/fable-edge-setup-001/deferred-multiregion.log`。
三组控制器凭据全部结束前，五题总表不会宣称整个队列已经结束。
本轮于 2026-09-14 13:20 UTC 确认控制器均退出、模型原生资源均释放。
两题完成通过，三题因输出截断中断；队列退出不等于五题均完成评分。
详见 `docs/FABLE_EDGE_FIVE_REVIEW.md`。未擅自添加 64k 输出参数或清零重试预算。
