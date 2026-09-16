# 稠密观测重建 · 正式版本 v1

两题：s-204 自然对流、s-203 分岔流。模型看到匿名几何、物性／初态、稠密 U/p/T 观测，
自行推断边界与模型、建网格并运行；原始算例配置不公开。全部题面为英文。

本版本不覆盖旧任务、不改 Ground Truth。它测**公开观测的数值重建**，不声称唯一识别机制或已证明物理解收敛。

## 已确认并冻结的评分

| 归一化指标 | 满分区间 | 零分区间 |
|---|---|---|
| 体积加权 RMSE | ≤ 5% | ≥ 30% |
| 观测点最大误差 | ≤ 20% | ≥ 100% |

中间线性给分；每个场取两项分数的较小值，整题再取 U、T、p 中最小值。
`pass` 表示 reward=1；低于满分记 `fail`，但保留部分 reward。
s-203 表压扣除体积加权常数偏置后计分，同时保留原偏置；s-204 绝对压力不去偏置。
尺度见各题公开 schema：U 的 GT 体积加权 RMS，T/p 的 GT 极差。

原生失败、明确未使用规定初态、只后处理未演化等有证据的失败为零分。
基础设施异常或无法自动判清的可执行钩子／重启动来源不伪造零分：记未评估，交专家审阅。
它们保留在注册题目总数中，但暂不进入已评分 reward 分母。

## 证据与能力边界

- 同一物理坐标采样，不依赖模型网格数量、单元顺序或边界名字；必须全覆盖。
- 每个原生 `run` 保留求解前输入快照和求解后输出；重启动检查已记录的原生祖先。
- 评分只在副本中后处理，替换原控制／数值字典为测量所需设置，不再次执行原控制钩子。
- 原生 ASCII／binary、改网格与斜网格、边界重命名、错误值和恢复路径均有测试。
- 完整性检查只验证可观察证据，不是对任意恶意程序的形式化证明；不恢复或推断隐藏思维链。
- 当前自动测量面向单流体区域的标准原生 U/T/p 场；不能可靠处理的表示不得冒称物理答错。

发布依据：整套回归 171 项通过；启动／恢复专项另有 9 项通过（部分与整套重复，不能直接相加）。
两份 GT 原生重放覆盖率 100%，最大差异仅浮点舍入量级；没有重算完整参考解。
每题 private/qualification.json 绑定评分代码、公开输入、参考、用户确认的规则和实际测试 XML。

## 启动与查看

配置：[dense-reconstruction-astra.yaml](../../../experiments/dense-reconstruction-astra.yaml)。
使用 `/root/.codex-experiment`，Codex + gpt-6-astra xHigh；不发子 Agent。
两题串行，每题最多 64 次模型调用、累计 1000 秒原生命令；可看离线文档，不开放互联网。

```bash
python -m agentcfd_bench prepare experiments/dense-reconstruction-astra.yaml
python -m agentcfd_bench.launch experiments/dense-reconstruction-astra.yaml --allow-paid
python -m agentcfd_bench status /absolute/run/directory
python -m agentcfd_bench report /absolute/run/directory
```

启动器返回带 UTC 时间指纹的独立目录，保存冻结代码、任务、配置、日志和全过程。
同一配置仍在运行时重复调用启动器会返回已有运行，不再发起一份。
每题实时轨迹在 `trials/<task>/transcript.md`、`transcript.jsonl`；
提交后的结果在 `trials/<task>/grading/result.json` 和 `reward.json`。
控制器独立运行，不依赖主 Agent 持续在线。
