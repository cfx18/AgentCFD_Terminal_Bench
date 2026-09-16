# 稠密重建 grader 修复审阅（2026-09-16）

## 本轮范围与结果

只修复验收器，并重新验收 Astra xHigh 联网轮已经明确提交的 s-203／s-204。
不重新调用 Agent，不选取其他答案，不重跑求解器，不修改 GT、归一化尺度或评分阈值。
两题均使用原有 120 次调用、不限原生计算总用时的实验条件。

正式重验收已完成，两题均为 `eligible`，没有待审项或验收基础设施错误。
新旧评分的原始物理误差完全相同，变化只在有效性审计及正式分数的发布。

| 题目 | 任务 | 模型调用 | 正式 reward（等于数值匹配分） | 满分的主要障碍 |
|---|---|---:|---:|---|
| s-203 | 分岔流重建 | 96 | 0.804766 | 局部速度最大误差超出满分阈值 |
| s-204 | 自然对流重建 | 107 | 0.311095 | 局部速度误差较大；绝对压力也未达满分 |

`pass` 仍表示 reward=1；部分得分的 `fail` 是“未达满分”，不是接口失败、没有结果或全部物理都错误。
单次每题的两份结果也不是模型总体能力的统计估计。

## 1. 哪些是验收器问题？

| 原先阻断 | 实际证据 | 修复方式 | 未放宽的底线 |
|---|---|---|---|
| s-203：`initial_field_representation_requires_review:T/U/p` | 初始场头省略可选的 `location`，但类型、量纲、初值均正确，且实际原生计算成功 | 仅初始输入允许省略这个字段 | 显式写错 location、类型、量纲仍不放行；原有严格输出读取行为保持 |
| s-203：`nonmeasurement_function:energy` | `energyTransport` 原生解能量方程；内部 `viscousDissipation` 从速度梯度／应力计算耗散 | 按原生行为识别为 `physical_equation`，而不是只允许采样函数 | 未知源项、动态代码、外部库或替换场引用仍进入人工审阅 |
| s-204：`nonmeasurement_function:thermalEndpoint` | `runTimeControl` 根据实际计算压力的均值决定何时结束，不给场赋目标值；本题允许自选停止策略 | 识别已审阅的原生结束控制；同时核查引用的测量函数和条件类型 | 不自动放行未知条件或能触发其他操作的 `setTrigger` |
| s-204：`restart_not_bound_to_prior_native_fields` | 旧程序按随机 ID 排序挑父运行，可能选到后来的副本并沿错误链递归 | 只在更早派发的运行里，按原生时刻日志及精确文件哈希找来源 | 不使用近似字段匹配；缺失时间顺序、字段被改、证据校验失败均不授予正式分数 |
| 重评分代码身份不完整 | 原 `grader_identity` 覆盖传统 physics 模块，但遗漏顶层 dense 模块 | 加入 dense 评分、采样、来源审计等代码 | 旧资格证明和实验快照不覆写 |

这些修复不要求 Agent 写成隐藏配置模板，也没有改变速度、温度、压力的误差计算。
未覆盖的合法实现仍可能需要人工审阅；`review` 不表示作弊，`eligible` 也不是对所有对抗程序的安全证明。

## 2. s-204 的重启链是如何核实的？

| 原生派发序号 | 运行 ID | 加载时刻 | 其加载状态的来源 |
|---:|---|---:|---|
| 5 | `r-e5e61a56785846a6` | 0 | 规定的均匀初态 |
| 10 | `r-7d8f8958361644e6` | 700 | 序号 5 的原生输出 |
| 21 | `r-a11a876e4c674798` | 1486 | 序号 10 的原生输出 |
| 23 | `r-d1b13491c4be4ded` | 1486.1 | 序号 21 的原生输出；这次是最终提交 |

每一段检查 17 个加载文件的精确哈希（对应时间目录及网格），并验证父运行的不可覆盖收据、
实际计算过对应时刻的日志以及派发先后。最终场采样时刻为 1487.1。
不是把所有试跑连成一条链；没有被最终解加载的其他试跑不成为它的来源。

## 3. 数值分数来自哪些误差？

下表百分数都相对题目公开的固定归一化尺度，不是除以各场的绝对值或各自预测值。
例如 s-204 压力的 14.75% 不是说十万帕的绝对压力差了 14.75%。

| 题目／场 | 归一化 RMSE | 归一化最大误差 | 本场得分 |
|---|---:|---:|---:|
| s-203 U | 4.21% | 35.62% | 0.804766 |
| s-203 T | 2.03% | 14.08% | 1.000000 |
| s-203 p（去常数偏置） | 0.80% | 9.43% | 1.000000 |
| s-204 U | 12.07% | 75.11% | 0.311095 |
| s-204 T | 1.40% | 13.12% | 1.000000 |
| s-204 p（不去偏置） | 14.75% | 14.77% | 0.610017 |

便于专家判断的原始量：

- s-203：速度 RMSE 为 0.23934 m/s，最大误差为 2.02256 m/s；温度最大误差为 0.01279 K。
- s-204：速度 RMSE 为 0.01319 m/s，最大误差为 0.08206 m/s；温度 RMSE 为 0.27325 K、最大误差为 2.55679 K；绝对压力 RMSE 为 3.72556 Pa。

两题分别在 68107 和 78750 个参考物理位置采样，覆盖率均为 1。
这些数据支持“全局／局部场重建还不够准确”的判断，不能单凭误差就断言某种边界条件错误、
网格未收敛或模型完全没有理解物理；定位原因仍需要与操作轨迹、网格和场图一起审阅。

## 4. 新的结果结构

先从可信原生结果独立采样，再分别给出数值评分和来源审计，最后合成正式成绩。

```json
{
  "grading_schema_version": "dense-result-v2",
  "reward_version": "dense-reconstruction-reward-v1",
  "metric_reward": 0.8047662055498264,
  "eligibility": "eligible",
  "reward": 0.8047662055498264,
  "verdict": "fail",
  "reason": "dense_reconstruction_below_full_credit"
}
```

同时保存逐场 `field_scores`、实际使用的误差、原始 `metrics` 和含来源链的 `integrity`。

| 有效性状态 | 正式 reward | 数值匹配分 |
|---|---|---|
| `eligible` | 等于数值匹配分 | 保留 |
| `invalid`（确认违反有效性要求） | 0 | 已有可信测量则保留，否则 null |
| `review`（证据待审） | null | 已有可信测量则保留 |
| `error`（基础设施异常） | null | 若采样已成功、仅审计出错，仍保留 |

RMSE 的满分／零分锚点仍为 0.05／0.30，最大误差为 0.20／1.00，中间线性插值，
每个场取两个指标的较低分，再对 U、T、p 取最低分。不开新费用或调用惩罚项。
报告保留总注册数、每种有效性状态数量及正式分数分母；诊断分数的均值单独标注，不冒充正式均分。

## 5. 精确代码与测试入口

- 数值分与有效性合成：`agentcfd_bench/grading/dense_rubric.py` 的 `metric_score`、`score`。
- 来源、初始场和重启链：`agentcfd_bench/grading/dense_integrity.py` 的 `inspect`。
- 原生函数的行为分类：`agentcfd_bench/grading/dense_functions.py` 的 `classify`。
- 严格字段读取：`agentcfd_bench/grading/physics/foam/science_metrics.py` 的 `field_values`。
- 采样、基础设施错误及 reward 投影：`agentcfd_bench/grading/dense_native.py` 的 `grade`、`publish_reward`。
- 报告及分母：`agentcfd_bench/reports/summary.py` 的 `report`、`markdown`。
- 不覆盖旧记录的修复回放：`agentcfd_bench/grading/regrade.py` 的 `regrade`。
- 本轮核心回归：`tests/test_dense_integrity_v2.py`、`tests/test_dense_release.py`。
- 恢复／不可覆盖证据回归：`tests/test_regrade.py`、`tests/test_dense_grading_lifecycle.py`。

测试结果：全套 266／266 通过（339.71 秒），代码身份相关补测 37／37 通过（7.11 秒）。
两轮有重叠，按测试 ID 去重共 267 个用例；没有失败或跳过。补测包含本轮最后增加的代码身份回归。
除单元／假模型测试，还覆盖真实 OpenFOAM 跨网格、重命名边界和二进制场采样。

- [全套测试证据](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/dense-grader-v2-regression-20260916.xml)
- [补充测试证据](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/dense-grader-v2-identity-regression-20260916.xml)
- [s-203 完整重验收结果](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/runs/dense-reconstruction-web/20260916T053705.904691Z-f87424c3/trials/s-203/regrades/20260916T071352.357247Z-adedd9a3/result.json)
- [s-203 新旧状态与提交绑定](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/runs/dense-reconstruction-web/20260916T053705.904691Z-f87424c3/trials/s-203/regrades/20260916T071352.357247Z-adedd9a3/intent.json)
- [s-204 完整重验收结果及重启来源链](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/runs/dense-reconstruction-web/20260916T053642.688204Z-f6d46f68/trials/s-204/regrades/20260916T071352.416988Z-151075fa/result.json)
- [s-204 新旧状态与提交绑定](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/runs/dense-reconstruction-web/20260916T053642.688204Z-f6d46f68/trials/s-204/regrades/20260916T071352.416988Z-151075fa/intent.json)

重验收完成后额外核对：旧评分文件、原提交、题目／GT 身份和各场原始误差均未改变；
模型调用仍为 96／107 次，求解器试跑总数仍为 13／12 次。
此次只各新增一次独立采样，约耗时 3.97／3.72 秒，不推进求解时间。
两个正式分数均已通过事务状态指针发布，重复生成报告得到一致内容。

## 6. 如何查看结果／以后再回放？

在 `AgentCFD_Terminal_Bench` 目录使用项目 `.venv-eval` 中的 Python：

```bash
python -m agentcfd_bench report /absolute/run/directory
python -m agentcfd_bench status /absolute/run/directory
```

这两个入口只读记录，不重新评分。明确要求再次验收时才执行：

```bash
python -m agentcfd_bench regrade /absolute/run/directory s-203
```

每次重验收会创建新的 `regrades/<UTC指纹>/`，保留 intent、代码快照、独立采样、result、reward、commit。
原 `grading/result.json` 保留；当前报告跟随事务状态中的 `grading_result` 指针。
本轮不会修改旧任务的资格证明、自动发布新任务版本或启动付费实验。
