# Astra xHigh 重测：只移除 task_contract

用户明确授权停止旧轮、移除 task_contract、在新目录重跑同样四题。

## 唯一评分改变

- 新任务版本：`expert-output-v1`；旧 `expert-reference-v1` 及旧成绩保留。
- 不执行输入与隐藏模板的物理配置比较。运行记录中的 contract 为
  `passed: null, status: not_evaluated`，不是补造通过。
- 正式检查项只有 `native_completion`、`field_realizability`、
  `reference_observations`、`report_matches_artifacts`。
- GT 数值、误差阈值、公开题面、几何、文档、模型、预算均不改变。
- 不新增 maximum-error、不重写物理语义判定、不修改 Agent harness。
- 输入安全、可信几何、独立运行、原生场提取、证据绑定和报告格式仍保留。
  支持的网格／输出表示限制未扩展；此轮不是任意 OpenFOAM 表达的通用验收器。

## 代码入口

`output_reference.OutputReference` 复用既有数值验收，仅移除 task_contract。
`output_release.build` 发布新四题包，逐字保留公开文件和 accepted-target.json。
`experiments/science.yaml` 选择新 profile，原有时间戳归档和独立控制器执行。

模型仍为 Codex subscription / gpt-6-astra / xhigh；任务顺序
s-205 → s-203 → s-202 → s-204；每题 64 次模型调用；单次与累计 OpenFOAM
预算均为 1800 秒；串行运行。无额外在线烟测。

## 本地回归与启动

测试覆盖旧 Astra 顺序误判的只读回放（不覆盖旧结果）、GT 不合格仍失败、
报告造假仍失败、缺失证据不通过、旧版仍保留 contract、新四题真实参考回放，
以及现有 CLI／隔离／中断恢复发布测试。执行结果以 audits 下 XML 与源码绑定记录为准。

```bash
bash ci_checks/science.sh prepare
bash ci_checks/science.sh check
bash ci_checks/science.sh submit --allow-paid --run-name astra-output-xhigh
```

每次 submit 自动创建新时间戳目录。模型轨迹、原始请求、结果和配置快照全部保留；
启动成功不等于物理验收通过。测试证据未就绪时 check/submit 拒绝运行。
