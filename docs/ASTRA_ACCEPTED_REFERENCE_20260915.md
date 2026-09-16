# Astra xHigh × four English physics tasks

## 本轮条件

用户确认：现有 s-202～s-205 数值算例作为 Ground Truth；公开题面为英文；模型自行划网格。
2026-09-15 又确认单次 OpenFOAM 上限提高至 1800 秒、累计仍为 1800 秒；不额外调用在线烟测，
本地测试完成后直接启动正式四题。此处不是历史 Sol / Fable / Kimi 成绩。

|设置|实际配置|
|---|---|
|Agent 骨架|已安装的 Codex CLI 0.153.4|
|模型|`gpt-6-astra`，`xhigh`，不自动替换模型|
|后端|ChatGPT subscription，原生 Responses 流式协议|
|子 Agent|明确关闭|
|任务顺序|s-205 → s-203 → s-202 → s-204|
|公开输入|英文物理要求、提交协议、观测格式、只读几何；没有配置模板|
|资料|筛查并冻结的 OpenFOAM v2306 docs；没有互联网|
|调用预算|每题累计 64 次；无 benchmark 单次输出 token 上限|
|OpenFOAM|单次/累计均不超过 1800 秒；串行，申请 35 分钟独立租约，不在等模型时占节点|
|接口证据|真实 Codex 可执行文件 + 本地假 Responses 服务的隔离/工具/恢复测试；不是在线探测|
|审阅记录|每题实时 `transcript.md`、`transcript.jsonl`，保留原始请求、工具输出、提交和验收|

## 接通的位置

```text
experiments/science.yaml
  → ci_checks/campaign_config.py（显式 model / profile / budget）
  → tasks/releases/expert-reference-v1/{s-202,s-203,s-204,s-205}
  → ci_checks/submit_science.py（检查、时间指纹归档、独立后台启动）
  → ci_checks/run_science_matrix.py
      ├─ accepted_release.qualify（只读回放已完成参考；不重跑 CFD）
      └─ engine.run + Codex 原生 Responses
          → 独立 OpenFOAM → accepted_reference.evaluate → 原始记录和成绩表
```

新的库文件：`accepted_reference.py` 负责验收；`accepted_release.py` 负责显式发布和参考证据回放。
旧 grader、旧任务版本和旧实验均不修改成绩。`public-task.json` 是唯一公开物料清单；
`solution/accepted-target.json`、参考配置、原生来源和评分代码留在宿主，不挂载给 Agent。

## 到底如何判分

必须满足：输入物理约束、原生运行完成、场的基本合理性、模型报告与真实场一致、定量参考比较。
独立执行器重新提取数据，不接受模型自报“我通过了”。

|题目|参考比较|仍记录但不作为额外收敛门槛|
|---|---|---|
|s-202 / s-203|固定物理分区的场 RMS 差；沿用 5% 尺度和温度 0.01 K 绝对底限|能量平衡证据；缺少证据明确 `not_evaluated`|
|s-204|温度剖面差/冷热温差 ≤5%；速度剖面相对 L1 ≤10%；冷热壁热流相对差 ≤5%|残差、末两次写出变化、净壁面热流不平衡和求解器收敛声明|
|s-205|40 个物理轴向分箱与已接受数值解比较，沿用初始状态尺度的 L1 ≤4%|独立解析 Riemann 解误差；原有守恒、状态方程和一维性仍为硬检查|

这是 **与专家接受的有限分辨率数值目标相符**，不是“证明连续方程高精度收敛”。
明确输出 `acceptance_version: expert-reference-v1`、`reference_status: accepted_by_expert`、
`convergence_certified: false`，不篡改旧版 `qualified` 字段。没有新增分段 reward 权重。
尤其 s-204 不要求猜到参考用了 6000 次迭代：执行器按模型提交的 `endTime` 检查完成，随后比较实际场。

限制也保留：s-202/203 的空间分区按单元中心归属并以体积加权，不是任意切割单元的精确交叠积分；
s-204 支持正交张量网格；s-205 支持每个横向一层单元的一维正交网格。输入物理检查仅支持现有解析表示，
并非所有物理等价的 OpenFOAM 写法都能识别。这些是当前测试条件，不能把所有拒绝都归因于物理理解不足。

## 自行提交

从 `AgentCFD_Terminal_Bench` 目录运行：

```bash
bash ci_checks/science.sh check
bash ci_checks/science.sh submit --allow-paid --run-name astra-xhigh
bash ci_checks/science.sh status --run-dir /path/printed/by/submit
```

本次会生成准备快照。日后改 YAML 后必须换 `name`，重新 `prepare`，不能修改既有快照来恢复旧运行：

```bash
bash ci_checks/science.sh prepare
```

`release.ready` 不替代测试证据。源代码、模型、effort 或客户端变更都要有匹配证据。
`evidence.interface_check: local-only` 是本轮用户明确选择：本地证据里 `provider_verified:false`，
正式首题才首次访问订阅服务；认证/额度错误保留为基础设施问题，未知请求不自动重发。

旧自定义 API 仍可选 Sol / Fable / Kimi；切换时用 `custom-api`、`reasoning_effort:null`、
`public_decision_log:false`、宿主 `env_file` 和 `interface_check:live-probe`，提供该接口原有真实探测证据。
Astra 工具请求不接旧 Chat 转换桥，避免默默丢失原生工具语义。

本次任务包很小，未复制完整 CFD 输出。所选参考的原始回执在本机 `audits/`，路径和哈希被冻结；
迁移到另一台机器时必须一并保留这些来源及其 allocation/release 回执。缺失会阻止启动，不重跑补造。

## 验证证据

结果目录：`audits/astra-accepted-reference-20260915-001/`。
`qualification/` 记录四个已有真实原生结果的只读回放（不是模型成绩）；`tests-release.xml` 记录完整回归
（1349 通过、3 项历史候选回放跳过）；随后修复启动工作目录的导入优先级问题，
`tests-launch-fix.xml` 及绑定文件为实际启动版本的相关回归与门禁证据。
`local-interface-launch-fix/` 记录用户选择的本地接口检查方式，不冒充官方成功响应。
测试中的假 Agent / 假 API 仅验证工程流程，不能计入正式题目分数。

`preliminary.xml` 是初始回归；`tests.xml`、`tests-final.xml` 为开发中主动中断的回归，均不作发布证据。
其中旧测试固定要求默认配置永远 `ready:false`、旧版本模拟配置误继承新 1800 秒预算的断言已修正；
历史阻断、原始失败和中断记录仍保留。另修复了 `science.sh` 在普通终端缺少包导入路径的问题，
新增从任意工作目录、不继承 `PYTHONPATH` 的实际命令测试。

首次正式启动在模型派发前退出：`python -c` 从项目工作目录误导入了可编辑源码而非冻结快照，
因而找不到仅存在于快照中的 `yaml-generated-s-205.json`。此时没有后台模型控制器、没有订阅请求。
启动器增加 `-P` 禁止该隐式工作目录导入，并用“工作目录就是项目本身”的完整复现测试覆盖。
失败归档 `astra-xhigh-20260915T135523503968Z-d405d5ef9c96-ec672ec1` 保留，不伪装成模型失败或恢复旧请求。
