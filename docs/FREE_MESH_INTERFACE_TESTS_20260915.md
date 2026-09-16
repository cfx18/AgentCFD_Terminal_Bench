# 本地接口补跑：中文结果与证据

结论：临时容量阻断恢复后，已完成本轮接口补跑。按唯一测试项统计，**1120 项最终通过，3 项未运行**。
没有调用付费模型，没有提交 OpenFOAM 集群作业，没有启用子 Agent；这不是模型成绩。
生产代码、测试断言、任务、Ground Truth 与实验配置均未修改。

## 数字怎样汇总

|步骤|本次结果|说明|
|---|---|---|
|完整基础回归|1060 通过，63 跳过，0 失败|恢复本地 socket 权限后执行；耗时约 150 秒|
|真实 Codex xhigh 专项|1 通过|从上述跳过项补跑；文件操作、文档、隔离和会话恢复|
|其余客户端集成测试|58 通过，1 失败|补跑四类真实客户端，耗时约 635 秒；失败原因见下节|
|失败项短路径复测|1 通过|同一代码、同一断言，仅恢复短临时目录|
|去重后的最终状态|1120 通过，3 未运行|原注册 1123 项全部保留，没有把重复复测算成新测试|

三项未运行的测试属于历史 Ultra 条件；当前明确选择 xhigh、关闭子 Agent，所以没有执行它们：

- `test_science_codex_integration::test_real_codex_build_run_fix_postprocess[chatgpt-subscription]`：该历史夹具内部使用 Ultra。
- `test_subscription_backend::test_real_subscription_transport_files_isolation_and_resume`：Ultra 路径。
- `test_subscription_backend::test_real_ultra_child_calls_are_counted_and_isolated`：主动派生子 Agent 路径。

## 唯一失败：本次测试临时目录选得太长

错误原文：`ValueError: Broker socket path too long`。

为保存轨迹，我把 pytest 临时目录放进了较长的项目归档目录。独立 namespace 测试直接在该目录下创建
`api/broker.sock`，触发已有 socket 路径长度保护。它发生在创建 socket 阶段，没有派发 API 请求。
这是本次测试启动路径设置错误，不是模型答错，也不是中转站返回错误。

复测时恢复 pytest 默认短临时目录，原测试立即通过；**没有删除路径保护，没有放宽隔离断言，也没有修改生产适配器**。
生产 Codex 适配器本来就通过短临时目录放置 socket，证据目录可以独立使用长路径。
以后本地 socket 测试使用短临时目录，完成后再归档轨迹；不要把长归档路径直接用作 `--basetemp`。
第一次失败的 XML 与复测 XML 都保留，不把失败报告改写成绿色报告。

## 验证了哪些行为

- Codex、FoamClaw、Claude Code、Kimi Code 真实客户端的文件操作、工具调用、文档查询及会话恢复。
- 正常提交、原生失败反馈、再次修改、读取返回场并独立后处理的端到端接口。这里原生服务是测试替身，不是新跑的物理参考。
- 已知 HTTP 错误、截断与未知请求正确区分；未知请求不盲目重发；SDK 辅助请求和重试计入预算。
- 最后一次允许的工具调用仍可提交新动作；旧动作不能在恢复后被误提交。
- 宿主、认证、参考、验收器不可见；文档和返回工件只读；外网不可达。
- xhigh 请求不启用子 Agent，适配器不注入单次输出 token 上限。

特别是 xhigh 专项：真实客户端完成两个连续回合，共 4 次本机假 API 请求，4 次 HTTP 200 和完整终止响应。
恢复后沿用原会话；文档检索与隔离断言均通过。模型名只是接口绑定，不能把它解读为 Sol 或 Kimi 的解题成绩。

## 可复查的证据

- [完整基础回归 XML](../audits/free-mesh-tests-20260915-002.xml)
- [Codex xhigh 专项 XML](../audits/free-mesh-xhigh-tests-20260915-001.xml)
- [59 项集成测试 XML，保留首次路径失败](../audits/free-mesh-interfaces-tests-20260915-001.xml)
- [短路径复测 XML](../audits/free-mesh-namespace-tests-20260915-001.xml)
- [xhigh 实际请求、响应、工具事件与恢复记录](../audits/free-mesh-xhigh-client-20260915-001/)
- [四类客户端完整测试轨迹](../audits/free-mesh-interfaces-20260915-001-evidence/)

四份 XML 都有测试期间生成的 `.binding.json`。已核对测试前后源码一致，并与当前代码一致；
失败报告也核验其内容和绑定，只是不能把它当作一次全绿运行。
基础回归与 xhigh 专项合并后通过 `core-and-subscription-xhigh` 测试门禁，缺失必需测试为零；
也验证了它们匹配现有 `runs/prepared/free-mesh-s001-review-001/runtime` 冻结代码。
s-001 已有的真实原生资格仍与当前代码绑定，没有重复跑求解器。

## 尚不代表什么

测试门禁通过不等于付费就绪，也不证明官方模型实时额度可用。
没有自动修改已冻结配置；后续新实验需显式引用基础回归和 xhigh 两份证据，并重新 prepare。
`release.ready` 仍为 false，在线模型接口资格和人工发布审阅仍需单独完成。
其余九道自主网格物理题的 grader 与 Ground Truth 工作未在此次接口补跑中完成，见[实现状态](FREE_MESH_IMPLEMENTATION_20260915.md)。
