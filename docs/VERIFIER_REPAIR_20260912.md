# s-001 验收器修复与历史复核

本次修复的是验收器误拒，不是降低物理标准。未重新调用付费模型，未重新运行求解器。
旧协议控制器 `1368550` 已通过 SIGINT 停止并保存中断记录；其遗留原生作业
`7941154` 经查询已不在队列中。未取消其他集群任务。

## 改了什么

| 问题 | 修复 | 仍拒绝 |
|---|---|---|
| `adjustTimeStep off` 被拒绝 | 按 v2306 Switch 的关闭别名检查：false/no/off/0/f/n/none | 开启、未知或多值写法 |
| `writeCompression` 只认 off | 支持相同关闭别名及缺省不压缩 | 开启或未知写法；不把 warning 后回退当成规范别名 |
| 省略 `edges` / `mergePatchPairs` 被拒绝 | 缺省与空列表等价 | 非空曲线边、合并补丁 |
| 未写 scale 被拒绝 | 默认尺度为 1；同时提供两种尺度键时都必须为 1 | 非单位尺度、未支持的网格变换 |
| 辅助配置文件一律被拒绝 | 删除 constant/system 的文件名白名单拒绝 | 任意文件中的宏、动态代码、库加载、路径越界等安全问题 |
| 带名称的 `nu` 触发 NameError | 补上字典解析器缺少的 `re` 导入 | 错误黏度、量纲或多余值 |

固定求解器始终由服务端选择，仍为 `icoFoam -noFunctionObjects`。不能通过
新增 `momentumTransport` 等文件偷偷换成另一个求解器。另补上显式的 `0/phi`
限制：这个输入确实会被 icoFoam 读取，不能用独立初始通量覆盖题目给定的静止初场。
这项支持边界已写入新版公开题面，不作为未公开规则。

本轮**没有**扩展为任意 OpenFOAM 表达方式的物理等价判定器。仍要求公开的
canonical 单块 4×20×1 网格及相应单元次序，不支持网格变换或任意非均匀网格。
边界条件、初场、黏度、时间、量纲和定量指标仍然受检。

## 验收流程没有删掉哪些保护

```text
输入快照 → 全文件安全检查 → blockMesh / checkMesh / icoFoam
                                  ↓
                     冻结原生输出与退出证据
                                  ↓
模型报告 → 独立提取量与报告比对 + 公开物理约束 + 解析解误差检查
```

速度剖面最大误差仍为 0.005 m/s；Uy RMS 仍为 1e-6 m/s；时间仍为
2±1e-8 s。报告与原生输出比较仍为绝对 1e-6 加相对 1e-5。残差仍只作诊断，
没有变成“残差低就通过”。哈希不符、证据不全不允许补造成功。

## 源码核查依据

本次不仅查文档，还读取了官方 v2306 源码：

- [Switch.C](https://api.openfoam.com/2306/Switch_8C_source.html)：`Switch::parse` 和 token 构造函数定义合法关闭别名。
- [IOstreamOption.C](https://api.openfoam.com/2306/IOstreamOption_8C_source.html)：压缩配置经 Switch 解析；未知值可能警告回退，不能当成合法别名。
- [blockMesh.H](https://api.openfoam.com/2306/blockMesh_8H_source.html)：尺度默认 1、edges 可省略。
- [blockMeshTopology.C](https://api.openfoam.com/2306/blockMeshTopology_8C_source.html)：`createTopology` 在没有 edges 时清空边列表。
- [mergePatchPairs.H](https://api.openfoam.com/2306/mergePatchPairs_8H.html)：使用 `readIfPresent`，不是必填项。
- [icoFoam/createFields.H](https://api.openfoam.com/2306/solvers_2incompressible_2icoFoam_2createFields_8H_source.html) 与 [icoFoam.C](https://api.openfoam.com/2306/icoFoam_8C_source.html)：直接读取 transportProperties 的 nu，构建层流动量方程，不启用 turbulenceProperties/momentumTransport/fvOptions 模型。
- [createPhi.H](https://api.openfoam.com/2306/src_2finiteVolume_2cfdTools_2incompressible_2createPhi_8H_source.html)：phi 使用 READ_IF_PRESENT，否则从 U 生成。

## 历史证据复核，不是新一轮成绩

复核了 `kimi-four-harness-science-002` 与 `kimi-four-harness-rounds-003`。
每次复核绑定原输入哈希、固定运行环境/命令、退出记录、日志、原生结果与冻结
结果副本，再对原模型报告重新验收。来源文件只读，复核另存。

| 批次 | Harness | 原模型报告数 | 旧通过 → 新通过 |
|---|---|---:|---:|
| 002 | Codex | 1 | 1 → 1 |
| 002 | FoamClaw | 5 | 0 → 5 |
| 002 | Claude Code | 0 | 不补算 |
| 002 | Kimi Code | 1 | 1 → 1 |
| 003 | Codex | 2 | 0 → 2 |
| 003 | FoamClaw | 1 | 0 → 1 |
| 003 | Claude Code | 1 | 0 → 1 |
| 003 | Kimi Code | 0 | 不补算 |

共 11 次报告，9 次误拒修正；原有 2 次通过未退化。这是**报告提交次数**，不是
11 道独立题。新反馈可能改变模型后续行为，因此不能把此表当作新协议下的
harness 排名或调用成本比较。

未掩盖的问题：

- 002 FoamClaw 最后的 r-000006 改成了 8×40×1 网格，仍不符合公开网格约束，
  也没有对应后处理报告。前面有效报告的误拒被修正，不代表所有运行都合格。
- 003 Codex r-000005 缺少完整原生 result，单列待审；没有重发原任务或补判通过。
- 003 Kimi Code 已有一次完整原生运行，但中断时尚未提交后处理报告，不补造模型报告。
- 002 Claude Code 的模型调用异常不是验收器问题，本次没有改写该历史结果。

逐报告原因、独立提取数值及输入哈希：
[可读复核表](../runs/verifier-v2-offline-audit-001/report.md)，
[带哈希的完整复核记录](../runs/verifier-v2-offline-audit-001/audit.json)。

## 代码入口与复现

- `tasks/s-001/tests/acceptance.py`：安全、公开物理约束、独立提取及最终验收。
- `agentcfd_bench/foam/dictionary.py`：维度标量解析修复。
- `agentcfd_bench/audit_acceptance.py`：仅重读证据的复核工具，不负责模型或原生执行。
- `tests/test_acceptance_semantics.py`：等价写法正例与物理/安全反例。
- `tests/test_acceptance_audit.py`：证据丢失、篡改、原生退出矛盾及无报告情况下的封闭失败。

从项目目录运行，必须指定一个**不存在**的新输出目录：

```bash
python -B -m agentcfd_bench.audit_acceptance \
  --campaign runs/kimi-four-harness-science-002 \
  --campaign runs/kimi-four-harness-rounds-003 \
  --output runs/my-new-offline-audit
```

## 版本与测试

新任务版本 `couette-transient-2`，登记摘要
`47af4194ba004c89c8c668eb4940da1dc1891525f94c921d461bf13e8047f249`。
两个当前实验配置已指向新任务；旧预算模式兼容配置仍保留其预算区别，没有
重新添加单次输出上限。旧任务、原配置和受影响解析器源文件已归档为
`docs/s001-verifier-v1-source-20260912.tar`，SHA256：
`5bf8be4a03eedaec20717867dfa2f02e78b66ed0a43964c576f146b7447728e8`。
旧运行目录完全保留，新代码拒绝恢复旧任务版本，不混用反馈。

全量测试 **262 passed / 0 failed / 0 skipped，84.29 秒**。包括四个真实 CLI
连接本地假 API 的文件操作、隔离和会话恢复测试，以及新加 74 项回归。
[JUnit 原始记录](verifier-v2-test-results-20260912.xml)。

这是离线/假 API 回归加历史真实原生输出复核，**不是新一次 OpenFOAM 原生
资格运行**。旧代码资格证据已因源码/任务摘要变化失效；下一轮付费执行必须
在新证据目录通过原生正负对照，再显式 `--allow-paid`。本次未自动启动。
