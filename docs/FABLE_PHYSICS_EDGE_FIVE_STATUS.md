# Fable 5：五题物理理解实验启动状态

2026-09-14 13:20 UTC 更新：四道新增题已实现，第二轮 828 项免费回归通过。
五题均已实际调用 Fable；两题完成通过，三题因上游 4096-token 输出截断中断。
有限续接已结束，控制器退出，原生资源释放。**不是五题已全部测完，也没有最终五题准确率。**
完整结果与归因看 `docs/FABLE_EDGE_FIVE_REVIEW.md`。
最新计数请看 `runs/fable-edge-five-report-001/summary.md`；
代码及本轮验收范围看 `docs/FABLE_EDGE_FOUR_IMPLEMENTATION.md`。
以下保留首题完成时的历史状态，不能用于判断当前四题是否已就绪。

2026-09-14 11:17 UTC 更新：首题付费实测已完成且通过，另外四题仍未就绪。
这不是“五题全部启动”或“五题完成”的报告。

配置：`experiments/fable-physics-edge-five-v1.candidate.json`。
该文件是设计清单，不符合正式 runner 的实验 schema，不能传给付费入口。
候选总清单仍为 `status=candidate_not_executable`、`paid_ready=false`；
首题单独经过资格门禁后，使用正式单题配置启动。

## 已完成的首题

首题 `s-105`：11 次模型调用，2 次原生提交（第一次建网格失败、第二次完整运行成功），
首次报告即通过全部验收，正式试验基础设施异常 0 次。
详细审阅见 `docs/FABLE_EDGE_S105_REVIEW.md`。
这是五题计划中 1 题完成，不能从中计算五题的最终通过率。

- 模型：中转站请求和响应均为 `AWS-Claude-Fable-5`，不替换模型。
  这是实际接口身份，不是对中转站背后权重来源的独立认证。
- Harness：真实 Codex CLI 0.153.4，通过共享 Chat 桥接；未使用关闭 thinking 的 judge 路径。
- 公开条件：空匿名目录；允许查询固定只读 OpenFOAM v2306 文档；不允许公网搜索。
- 隔离：不向 Agent 挂载参考、验收代码、历史成绩、宿主密钥或 OpenFOAM 求解器。
  OpenFOAM 由独立的隔离集群环境执行。
- 预算：累计 64 次模型请求，原生运行累计 600 秒、每次最多 120 秒，单次 API 超时 600 秒。
  不新增输出 token、累计 token 或费用上限；调用失败与未知结果单列。
- 固定代码：`runs/fable-edge-runtime-001/`，本次运行不会使用后续开发修改。
- 正式配置：`experiments/fable-edge-01-s105-v1.json`。
- 实时结果：`runs/fable-edge-live-001/s-105/scoreboard.md` 和 `scoreboard.json`。
- 控制器日志：`runs/fable-edge-setup-001/science-controller.log`。
- 完整模型记录：`runs/fable-edge-live-001/s-105/agent/<session>/submission-*/`。
- 原生输入与结果：`runs/fable-edge-live-001/s-105/native/`、`results/`。
- 启动程序：`ci_checks/run_codex_science.py`。独立进程运行，无需用户继续回复才能前进。
  已知原生排队状态只观察同一操作，不补发不明 API 请求。

计数说明：实时表中的 model_calls 在一次 Agent 提交回收后入账；提交进行中，
查看 `submission-*/api/call-*/dispatch.json` 可看到已经发出的请求。
不能将表中暂时未更新的计数当成模型停滞。

## 五题

| ID | 原版 tutorial | 重点 |
|---|---|---|
| edge-01 | incompressible/pimpleFoam/RAS/TJunction | 压力驱动、出口不对称、标量源项 |
| edge-02 | heatTransfer/chtMultiRegionFoam/multiRegionHeater | 接触热阻、允许温度跳变、恒温边界不是固定功率 |
| edge-03 | incompressible/pimpleFoam/RAS/TJunctionArrheniusBirdCarreauTransport | 原参数无剪切变稀，但不能删掉温度依赖及能量输运 |
| edge-04 | heatTransfer/buoyantSimpleFoam/buoyantCavity | 浮力、三维无滑移墙、绝热与热平衡 |
| edge-05 | compressible/rhoCentralFoam/shockTube | 可压缩热力学、初始间断与波传播 |

第五题选用此前建议中的 shockTube；前三类新增物理题与现有 s-105 对照均保留。
不从失败样本中回头调整题目或阈值，不把基础设施异常计为物理失败。

## 已完成的就绪检查

- 完整阅读桥接技能及桥接参考，确认真实客户端、隔离、文档和原生资格门禁。
- 加入 Codex 的显式模型身份，不再将共享桥接固定为 Kimi-K3；其他客户端不冒充已经适配 Fable。
- Codex 旧接口/兼容测试：31 项通过。
- 显式模型与真实客户端回归：27 项通过，包括实际 Codex 对接本地假 API、读写文件、
  匿名目录隔离、文档访问、原生提交与报告。该组没有调用付费模型。
- 付费接口探测：直接工具探测 2 次请求，第二次 HTTP 200 但 `finish_reason=content_filter`、
  零输出；保留在 `runs/fable-edge-provider-probe-001/`，不计作物理失败。
- 实际 Codex + Fable 探测：3 次请求通过；完成文档搜索、文件写入与读回。
  记录在 `runs/fable-edge-client-probe-001/`；搜索成功不等于读取了完整文档页。
- 首题原生资格：6 项检查全部通过，包括原版参考、缺少 U 的失败对照、能运行但
  物理错误的零标量源对照、伪造报告、合理数值参数调整和全场差异检测。
  证据在 `runs/fable-edge-native-qualification-001/s-105/`。
- 启动器单元测试：4 项通过。全部历史成绩、原始请求和失败探测均保留。
- 最终完整本地回归：789 passed、0 failed、0 skipped；真实客户端使用本地假 API，
  没有调用其他付费模型。证据：`runs/fable-edge-setup-001/regression-host-tests.xml`。
  接口探测/启动器附加测试共 12 passed，证据：`probe-runner-tests.xml`。
  首次在禁止 socket 的受限沙箱执行时为 683 passed、47 权限失败、59 skipped，
  原始 `regression-tests.xml` 保留；在有 namespace/socket 权限的测试环境完整重跑后全绿。

真实客户端会提示该中转站模型名不在 Codex 内置模型目录中，使用 fallback metadata。
这条警告已留在完整 events.jsonl；未因此冒称获得上游完整隐藏 reasoning。
桥接请求不强行注入 thinking、temperature 或输出 token 上限。

## 另外四题尚缺的能力

| 题目 | 尚未完成 | 当前是否付费调用 |
|---|---|---|
| multiRegionHeater | 多区域预处理、分区域输出提取、热阻/热平衡验收、原生正负对照 | 否 |
| 温度依赖黏度分支流 | energyTransport 安全支持、温度和黏度验收、原生正负对照 | 否 |
| buoyantCavity | 浮力求解器运行配方、温度/压力单位提取、热平衡验收、原生正负对照 | 否 |
| shockTube | setFields 初始化与可压缩求解器配方、热力学输出提取、原生正负对照 | 否 |

四题保留在五题清单中，不用旧简单题代替，不从分母静默删除。
因此当前单题 scoreboard 的 1 个注册任务不能当作整个五题研究的分母。

代码依据（不是正在等待中转站）：

- `agentcfd_bench/execution_spec.py:10` 仅登记 icoFoam/simpleFoam/pimpleFoam；
  第 49 行还固定要求前三步为 mesh、mesh_check、solver，不能直接插入 setFields
  或多区域分网格步骤。
- `agentcfd_bench/runtime.py:235` 只收集两层目录，无法读取多区域的 time/region/T。
- `agentcfd_bench/foam/science_inputs.py` 现有函数对象策略没有 energyTransport，
  不能把其必要能量方程误当危险代码删除后评分。
- `agentcfd_bench/foam/science_metrics.py` 的压力单位固定为运动压力，且要求末步
  Solving for p 残差。浮力的 p_rgh 和可压缩求解器不能套用这一规则。
- 原始 multiRegionHeater 是推进到 100 秒的五区域问题；buoyantCavity 是 1000 次
  稳态迭代，shockTube 是 0.007 秒瞬态。不能沿用 s-105 的 1.5 秒完成条件。

应先完成并测试这些类型边界，再各自准备一次原版参考与正负对照；
不能仅修改实验 JSON 的模型名/求解器名就声称另外四题已可测。

## 前一轮存储问题（历史）

2026-09-14 本轮准备时，部分已有代码与原始参考文件读取长时间未返回。
本地进程诊断曾返回 `fatal library error, lookup self`；最小 `/bin/sh` 命令
及新候选文件读取可以成功。部分先前读取后来恢复，但继续读取其他文件又停顿。
不能仅凭这些现象将根因确定为 Ceph 服务端、客户端或执行沙箱。

当时未调用 Fable API，也未运行 OpenFOAM。相关文件读取本轮已恢复；
这一历史描述不代表上方已经启动的首题。

## 其余任务上线顺序

1. 验证项目文件读取、审计落盘和退出凭据回收正常；不要重用缺证据的执行。
2. 检查既有凭据配置，仅记录非敏感模型身份，不导出密钥。
3. 为四个新增物理类型完成公开题面、运行配方、结果提取与私有验收插件。
   保留原版物理输入；物理阈值须在看模型答案之前完成资格验证并冻结。
4. 使用真实客户端 + 本地假 API 验证 Fable 传输所需适配、文档访问和隔离。
   固定文档查询与公网检索必须分别报告；不能把前者称为已联网检索。
5. 原版参考、正确等价配置、错误物理和伪造报告的原生对照全部通过后，
   冻结新代码/任务/模型/工具身份，再按用户授权启动五题 Fable 5 实测。
6. 保存全部查询、动作、输入快照、退出回执、原生结果和报告；可见 reasoning
   只按实际返回内容保存，不声称获得完整隐藏思维链。

用户已授权本次五题配置和 Fable 测试，无需因正常准备步骤再次索要付费启动许可；
该授权不允许跳过隔离/原生门禁、冒用其他模型，或把未完成的候选当成就绪实验。
