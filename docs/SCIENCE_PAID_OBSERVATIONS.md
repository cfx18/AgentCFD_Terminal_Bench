# 首批从零建模：逐题付费审阅记录

批次：`tutorial-science-matrix-001`；Kimi-K3；五题×四个真实 harness；
固定离线文档。本文记录已人工核对的具体事实，不替代
[实时完整分母表](../runs/tutorial-science-matrix-001/scoreboard.md)。
尚未完成的题目不填成失败；未审阅的轨迹不宣称已审阅。
不修改原始结果，也不向运行中的模型发送本文的私有参考误差。

## 当前维护状态（2026-09-13）

旧批次已因确认的验收反馈缺陷协作中断，控制器真实进程已退出。
保留 20 个注册试验：6 个完成（4 pass、2 fail）、1 个维护中断、13 个未开始。
这些是旧冻结版本的原始统计，**不是修复版最终排名**，不删掉受影响试验来提高分数。
本次没有重发模型请求。详见下文 AMI 问题及对照证据。

## 如何理解失败计数

- **提交格式失败**：harness 返回时 action 文件缺失或不符合提交协议；其中可能是
  没有执行承诺的动作，也可能是模型自写后处理失败、没来得及产生报告。不是全部都
  等于 OpenFOAM 字典语法错误。
- **原生启动失败**：原生命令失败且求解日志尚无 `Solving for ...`。
- **数值运行失败**：求解器已经出现 `Solving for ...` 后失败。这是发生阶段，
  不代表根因一定是数值发散；例如运行后才读取到缺失的 `pFinal` 也归于此阶段。
- **报告验收失败**：已经产生结构正确的报告，但其数值或最终物理输出没有通过验收。

判定根因必须结合每次日志及模型实际修改，不仅看汇总列名。

## 已完成结果的只读证据复核（2026-09-13）

对下列四个已完成试验额外复核了每次原生输入/任务/运行环境/命令身份与哈希、
开始和退出凭据、日志清理前后对应、冻结结果与公开产物逐字节一致、资源释放凭据；
再用相同冻结验收器读取已保存报告和产物，结果与保存的完整验收对象一致。
本次复核模型调用 0、求解器运行 0，不改写原始结果或模型获得的反馈。

| 试验 | 首次原生命令退出码 | 第二次原生命令退出码 | 报告重新验收 |
|---|---|---|---|
| s-101 / Codex | 0 / 0 / 1 | 0 / 0 / 0 | 与保存结果完全一致，pass |
| s-101 / FoamClaw | 0 / 0 / 1 | 0 / 0 / 0 | 与保存结果完全一致，pass |
| s-101 / Claude Code | 0 / 0 / 1 | 0 / 0 / 0 | 与保存结果完全一致，pass |
| s-101 / Kimi Code | 0 / 0 / 0 | 无第二次运行 | 与保存结果完全一致，pass |

三列退出码依次为 blockMesh、checkMesh、icoFoam。

## 首题完整对照（不是五题最终排名）

| Harness | 最终结果 | API 调用 | 原生运行提交 | 原生失败 | 后处理脚本失败 | 提交格式失败 | 模型耗时统计/s |
|---|---|---:|---:|---:|---:|---:|---:|
| Codex | pass | 19 | 2 | 1 | 1 | 3 | 427.020 |
| FoamClaw controlled | pass | 15 | 2 | 1 | 2 | 3 | 245.412 |
| Claude Code | pass | 45 | 2 | 1 | 3 | 0 | 629.654 |
| Kimi Code | pass | 9 | 1 | 0 | 0 | 0 | 335.709 |

API 调用、工具调用、harness 返回和原生运行不是同一个量。Kimi Code 首轮在一次
模型响应中产生多个 Write 调用，所以它的 9 次 API 请求不代表只做了 9 个动作。
耗时不是独立重复测量，受到上游响应与客户端行为影响；不能仅凭首题给总体排名。

### 模型与输出参数核对

检查首题全部 88 个已完成请求的 `wire_request.json` 和 `response.raw`：请求模型
及返回的模型标识均为 `Kimi-K3`；完成状态均为正常 stop 或 tool_calls，未出现
`finish_reason=length`。这些是 API 返回的身份，不是对中转商真实模型权重的独立认证。

| Harness | 实际发送的 max_tokens | 说明 |
|---|---|---|
| Codex | 未发送 | 使用客户端/上游默认行为 |
| FoamClaw | 未发送 | 使用客户端/上游默认行为 |
| Claude Code | 32000 | 保留当前真实客户端设置，不是 benchmark 额外注入的上限 |
| Kimi Code | 117935～131072，随请求变化 | 保留客户端按上下文计算的设置 |

因此准确说法是“benchmark 不额外强加单次输出上限”，不能说“四个客户端发出的
请求都没有 max_tokens”。本批次保持这些已冻结行为；没有为结果好看而中途改参数。

## s-101 / Codex：最终通过

2026-09-13 核对六次 harness 返回、两次原生运行与最终独立验收。
模型共 19 次 API 调用，19 次均有终态，无基础设施事件。

| 顺序 | API 调用数 | 实际行为 | 结果 |
|---|---:|---|---|
| 1 | 9 | 从空目录写入网格、字段、物性、数值字典，查一次文档并提交运行 | 网格及 checkMesh 通过；求解器初始化失败 |
| 2 | 2 | 根据原生日志补上压力参考并重新提交 | 完整运行至 0.5 s |
| 3 | 1 | 只说将计算报告，没有写新的 action 文件 | 提交格式失败，不是新的 OpenFOAM 失败 |
| 4 | 4 | 读取输出并编写后处理，残差正则表达式把逗号包含进数字 | Python 转换失败；未产生 action 文件，提交格式失败 |
| 5 | 1 | 只说将修复正则，没有执行修改或写新 action | 提交格式失败 |
| 6 | 2 | 实际修复正则并运行后处理，写出结构化报告 | 六项独立验收均通过 |

### 原生错误与实际修改

首轮求解器原文：

```text
Unable to set reference cell for field p
    Please supply either pRefCell or pRefPoint
file: system/fvSolution.PISO at line 44 to 45.
```

模型的第二次输入相对第一次只增加两行：

```diff
 PISO
 {
     nCorrectors     2;
     nNonOrthogonalCorrectors 0;
+    pRefCell        0;
+    pRefValue       0;
 }
```

因此这是封闭域压力参考遗漏，经原生反馈自行修复，不是中转 API 或验收器错误。
[原始清理后日志](../runs/tutorial-science-matrix-001/trials/s-101/codex/run/artifacts/r-000001/solver.log)。

### 三次格式失败究竟是什么

三次均没有生成 `system/science-action.json`，并非三份报告数值被判错。
中间一次后处理的实际异常为：

```text
ValueError: could not convert string to float: '5.33259e-08,'
```

另外两次是结束于文字承诺、没有实际提交。当前统一缺失 action 反馈使用 JSON
解析器原文 `Expecting value: line 1 column 1 (char 0)`，解释性不够好；本批次
不临时更改冻结的反馈。应把“提交协议失败”“后处理编程错误”“OpenFOAM
初始化失败”分开审阅，不能把表中的三个格式失败都解释为 CFD 知识错误。
每次 action 消费与真实事件保存在该试验 agent/ 下；
[六次输入输出快照](../runs/tutorial-science-matrix-001/trials/s-101/codex/run/turns/)。

### 最终验收证据

| 项目 | 实际值 / 结论 |
|---|---|
| 时间、网格 | 0.5 s；400 个单元 |
| 速度整场 relative L2 | 0.014907999（约 1.49%，阈值 5%） |
| 压力整场 relative L2 | 0.018620871（约 1.86%，阈值 10%；闭腔去除压力常数） |
| 速度整场 relative Linf | 0.041957763（阈值 50%） |
| 压力整场 relative Linf | 0.023539265（阈值 50%） |
| 速度单元 RMS | 0.251709889 m/s |
| 速度最大值 | 0.853062092 m/s |
| 物理配置、原生完成、场有效性 | 全部通过 |
| 自报数值与真实产物 | 全部一致，未发生报告验收失败 |

这是固定网格、预登记容差内的数值复现，不证明任意网格或全部等价数值配置均适用。
完整独立结果见
[验收 JSON](../runs/tutorial-science-matrix-001/trials/s-101/codex/run/evaluations/000006/result.json)。

### 成本与资源

- 模型执行耗时统计 427.020 s；原生执行累计 1.311 s；这不是包含集群排队/传输的整题墙钟耗时。
- 上游报告输入 354756 token（其中缓存 293746），输出 10456（其中推理 4225）；不重复相加。
- 上游未报告可识别费用，不能将费用缺失写成零。
- 文档搜索 1 次、全文阅读 0 次，返回 3000 字符；来自宿主查询凭据，不是模型自述。
- 原生启动失败 1 次、数值执行失败 0 次、提交格式失败 3 次；共 2 次运行提交。

计数与用量原始表：
[逐题 scoreboard](../runs/tutorial-science-matrix-001/trials/s-101/codex/run/scoreboard.md)。

## s-101 / FoamClaw controlled：最终通过

同一题、同一模型和同一文档条件；实际使用受控 FoamClaw 引擎，不是默认产品配置。
15 次 API 调用全部收到终态，无基础设施事件；6 次 harness 返回、2 次原生提交。

| 顺序 | API 调用数 | 实际行为 | 结果 |
|---|---:|---|---|
| 1 | 3 | 写入全部算例，检查文件后只说将写运行 action | 未写 action，提交格式失败 |
| 2 | 2 | 写入运行 action | 网格通过，求解器初始化因缺压力参考失败 |
| 3 | 2 | 在 PISO 中增加 pRefCell 0、pRefValue 0 并重新提交 | 运行完成至 0.5 s |
| 4 | 3 | 自写字段后处理，把标量列表元素误当子列表 | Python TypeError；未产生报告 action |
| 5 | 3 | 重写后处理，向量列表的嵌套括号解析错误 | 解析出 0 而非 400 个向量；未产生报告 action |
| 6 | 2 | 改用括号深度匹配提取列表并提交报告 | 六项独立验收均通过 |

两次后处理原始错误：

```text
pv = [x[0] for x in p]
TypeError: 'float' object is not subscriptable
```

```text
assert len(vals) == n, (len(vals), n)
AssertionError: (0, 400)
```

模型曾把第二个错误口头归因为行首空格；从实际正则代码可见，问题是非贪婪匹配
在嵌套向量的首个右括号就停止。这里采用执行代码和错误原文，不将模型的自我解释
当作诊断证据。最后的深度匹配实现正确提取了全部 400 个向量。

最终速度整场 relative L2 为 `1.048740731e-6`，压力为 `1.343576824e-6`；
两者 Linf 分别为 `5.863953924e-7`、`1.040243431e-6`，均通过预设范围。
真实报告、物理配置、场有效性和原生完成检查全部通过。
这些数值非常接近固定原版基准，但一题不构成 harness 排名。

- 模型耗时统计 245.412 s，原生执行累计 1.246 s（不含排队/传输等墙钟开销）。
- 输入 194440 token（缓存 87040），输出 7274（推理 1087）；费用未报告。
- 宿主文档查询凭据 0 次：有查询权限，但本次未使用。
- 原生启动失败 1 次、提交格式失败 3 次、数值运行失败和报告验收失败均 0 次。

证据：[逐题表](../runs/tutorial-science-matrix-001/trials/s-101/foamclaw/run/scoreboard.md)、
[独立验收](../runs/tutorial-science-matrix-001/trials/s-101/foamclaw/run/evaluations/000006/result.json)、
[六次快照](../runs/tutorial-science-matrix-001/trials/s-101/foamclaw/run/turns/)。

## s-101 / Claude Code：最终通过

45 次 API 调用均收到终态，无基础设施事件。3 次 harness 返回，2 次原生运行。
同样从空目录生成并自行后处理，没有文档查询。调用数包含客户端辅助调用，不能
把 45 次全部叫作主模型的 45 个自主解题步骤。

| 顺序 | API 调用数 | 实际行为 | 结果 |
|---|---:|---|---|
| 1 | 10 | 生成算例并提交 | 第一次压力求解后，因缺 pFinal 退出 |
| 2 | 12 | 补 pFinal；一次 Edit 因尚未先 Read 被客户端拒绝，读取后成功修改 | 第二次原生运行完成 |
| 3 | 23 | 编写后处理，在同一会话内修复三次脚本执行错误，提交数值报告 | 六项独立验收通过 |

首轮原生错误：

```text
Entry 'pFinal' not found in dictionary "system/fvSolution.solvers"
```

第二轮仅在 `system/fvSolution.solvers` 的原有 p 配置后补上：

```text
pFinal
{
    $p;
    relTol 0;
}
```

此处不是遗漏闭腔压力参考；pRefCell/pRefValue 从第一次配置中已经存在。
由于错误发生前已有 `Solving for p` 日志，它在原生统计中是 numerical 阶段，
但根因仍是缺配置，不是数值发散。模型并未更改规定物理条件来规避验收。

修复期间一次工具拒绝原文：

```text
File has not been read yet. Read it first before writing to it.
```

后处理脚本在同一次 harness 返回前出现的三次真实错误依次为：

```text
ValueError: /artifacts/r-000002/0.5/p
AssertionError: ('/artifacts/r-000002/0.5/U', 0, 400)
AssertionError: ('/artifacts/r-000002/0.5/U', 0, 400)
```

其中向量错误涉及嵌套括号的列表提取；模型逐步修复后才写报告。
因此本例提交格式失败为 0，但工具拒绝有 1 次、后处理脚本失败有 3 次。
只比较提交格式列，会遗漏发生在 harness 内部且自行恢复的错误。

最终速度整场 relative L2 为 `4.115093459e-6`，压力为 `2.160878935e-6`；
Linf 分别为 `2.345581569e-6`、`1.345290817e-6`。时间 0.5 s、400 个单元，
物理约束、原生完成、场有效性、自报数据一致性均通过。

- 模型耗时统计 629.654 s；原生执行累计 1.233 s。
- 输入 560716 token（缓存 442368），输出 10190（推理 2820）；费用未报告。
- 原生运行失败 1 次（缺 pFinal）、提交格式失败 0、报告验收失败 0。

证据：[逐题表](../runs/tutorial-science-matrix-001/trials/s-101/claude-code/run/scoreboard.md)、
[独立验收](../runs/tutorial-science-matrix-001/trials/s-101/claude-code/run/evaluations/000003/result.json)、
[三次快照](../runs/tutorial-science-matrix-001/trials/s-101/claude-code/run/turns/)。

## s-101 / Kimi Code：最终通过

9 次 API 调用，2 次 harness 返回；首轮 3 次调用完成所有配置及运行提交，
第二轮 6 次调用读取真实输出、自写后处理并提交报告。
原生一次运行通过，工具轨迹未观察到后处理脚本或文件操作失败，也没有缺 action。
这是受控 Node Kimi Code 客户端，不是 Python Kimi CLI。

原始输入已包含压力参考和 pFinal，不需要像其他试验一样根据报错补写。
首次响应批量调用 Write 写入 7 个配置文件，随后另写运行 action。
后处理先查看真实字段格式，再编写括号匹配解析器；脚本一次执行成功，报告通过。

最终速度整场 relative L2 为 `4.108871430e-6`，压力为 `2.371949915e-6`；
Linf 分别为 `2.310397846e-6`、`1.254895108e-6`。最终时间 0.5 s、400 个单元，
物理约束、原生完成、场有效性与自报数据一致性全部通过。

- 模型耗时统计 335.709 s，原生执行 0.694 s。
- 输入 287214 token（缓存 248832），输出 10178（推理 5738）；费用未报告。
- 文档查询 0 次；原生失败、后处理脚本失败、提交格式失败及报告验收失败均为 0。
- API 次数少于前三个试验，但模型耗时高于本题 FoamClaw；两者应分开报告。

证据：[逐题表](../runs/tutorial-science-matrix-001/trials/s-101/kimi-code/run/scoreboard.md)、
[独立验收](../runs/tutorial-science-matrix-001/trials/s-101/kimi-code/run/evaluations/000002/result.json)、
[两次快照](../runs/tutorial-science-matrix-001/trials/s-101/kimi-code/run/turns/)。

## s-102 / Codex：预算耗尽，最终失败；发现一项末轮提交误分类

正式状态 completed/fail，原因 model_budget_exhausted；64/64 次调用。
10 次原生运行（5 次完成）、38 次 harness 返回、原记录 4 次报告验收失败，
0 次基础设施事件。这不是整批排名。
模型必须完成 24 单元非共形 AMI 接口题、100 次 SIMPLE 迭代并自行后处理。

| 原生提交 | 结果 | 原始问题 | 后续实际修改 |
|---|---|---|---|
| r-000001 | 启动失败 | cannot find file "/work/constant/transportProperties" | 将 physicalProperties 改为 transportProperties，同时改 FoamFile.object |
| r-000002 | 启动失败 | cannot find file "/work/constant/turbulenceProperties" | 新建 turbulenceProperties，simulationType laminar |
| r-000003 | 启动失败 | Entry 'div((nuEff*dev2(T(grad(U)))))' not found | 在 divSchemes 增加该项 Gauss linear |
| r-000004 | 求解阶段失败 | Attempt to cast type lduPrimitiveMeshAssembly to type fvMesh | 压力求解器从 GAMG 改为 PCG/DIC |
| r-000005 | 运行完成，报告验收失败 | 物理约束和自报一致性通过，但 U/p 全场偏差超限 | 调整数值参数后再次运行 |
| r-000006 | 运行完成，报告验收失败 | 同上 | 改用 Gauss linear 对流离散 |
| r-000007 | 运行完成，报告验收失败 | 压力场已达标，速度场仍超限 | 尝试给 U 的 AMI 边界增加 useImplicit true |
| r-000008 | 启动失败 | Implicit option is not allowed for type: vector | 撤回 U 的 useImplicit，修改修正次数与松弛系数 |
| r-000009 | 运行完成，报告验收失败 | U/p 误差均增大 | 返回 bounded Gauss upwind；进一步调整线性容差和松弛 |
| r-000010 | 运行完成；末轮报告被预算边界误标未提交 | 报告其实已写出；只读审计仍未通过数值验收 | 调用已用尽，不再请求模型 |

GAMG 报错堆栈包含 faceAreaPairGAMGAgglomeration；模型换压力线性求解器，未为
通过原生启动而删除 AMI 接口。首四次错误和相应修改均能在原始快照中对应。

| 报告对应运行 | U relative L2 / 上限 | p relative L2 / 上限 | 自报数据与真实输出 | 物理配置约束 |
|---|---|---|---|---|
| r-000005 | 0.352899 / 0.10 | 0.485774 / 0.15 | 通过 | 通过 |
| r-000006 | 0.353300 / 0.10 | 0.475697 / 0.15 | 通过 | 通过 |
| r-000007 | 0.223856 / 0.10 | 0.112642 / 0.15 | 通过 | 通过 |
| r-000009 | 1.615670 / 0.10 | 2.579799 / 0.15 | 通过 | 通过 |
| r-000010（末轮只读审计） | 0.353852 / 0.10 | 0.327614 / 0.15 | 通过 | 通过 |

这证明此处不是伪造报告、API 故障或没有运行；但仅凭未通过固定参考场容差，
不能直接断言模型不理解物理意图。检查条件是固定离散网格的数值复现。
审阅时还应注意：原参考 div(phi,U) 为 bounded Gauss linear，模型此时为
bounded Gauss upwind，另有松弛系数、非正交修正次数和线性容差等差异。
没有单变量对照执行，因此不把误差确定归因于其中某一项，也没有为本次结果
临时修改容差或额外提供参考数值。

### “只说不做”是否是桥接丢调用

submission-10～13 的原始 response.raw 均为 finish_reason=stop、tool_calls 缺失，
内容只是“马上修改并提交”；对应 wire_request.json 中均有 7 个可用工具。
submission-14 随后正常返回并执行 exec_command。证据不支持这些回合是适配层
把已返回的工具调用丢失；不据此独立认证中转模型的质量或完整内部思考。
这些回合消耗正常 API 预算，缺 action 如实计作提交格式失败，没有免费重试。

证据：[实时逐题表](../runs/tutorial-science-matrix-001/trials/s-102/codex/run/scoreboard.md)、
[第一次数值验收](../runs/tutorial-science-matrix-001/trials/s-102/codex/run/evaluations/000008/result.json)、
[第二次数值验收](../runs/tutorial-science-matrix-001/trials/s-102/codex/run/evaluations/000015/result.json)、
[逐次输入输出](../runs/tutorial-science-matrix-001/trials/s-102/codex/run/turns/)。

### 必须单列的 harness 问题：有效末轮报告被忽略

第 38 次返回中，最后一次获准模型调用已经通过工具写出 r-000010 的有效报告。
客户端随后想再请求模型生成结束语，本地预算守卫拒绝；旧适配器因 budget_stop
将整个返回设为 submitted=false，尽管新 action 文件真实存在。因此原表中的
24 次格式失败应区分为 23 次 action 缺失和 1 次 harness 误分类。
23 次缺失中，21 次上游没有工具调用，另两次分别是后处理失败、查文档后未提交。

只读审计第 38 次保存文件，报告解析成功、自报量与 r-000010 产物全部一致，但
速度和压力仍超容差。因此**本题失败结论不变**；正确的审计计数是 23 次格式失败、
5 份未通过数值验收的有效报告，而不是原表的 24/4。原记录未覆盖，审计没有
新建模型答案、调用模型、重跑求解器或改变后续模型获得的反馈。

程序原因是 `smoke/agent.py` 用 `completed and not budget_stop` 决定 submitted，
没有区分“最后一个工具已写出新 action”与“没有提交”；此外本地预算守卫返回
可重试的 429，会令部分真实客户端继续退避。修复已先在独立副本验证，再应用
主项目，完整回归 536 项通过。旧矩阵已停止且代码归档；不能把修复后的行为
冒充已经用于早先试验。版本和测试证据见[修复说明](VERIFIER_BOUNDARY_FIX.md)。

### 其他过程与用量

- 后处理脚本一次失败：把 `Time = 100` 整行送给 int，模型后来自行修复。
- 原生失败 5 次：4 次 startup、1 次 numerical；后者是 GAMG 类型转换，不是普通数值发散。
- 模型耗时统计 1505.794 s，原生执行累计 8.984 s；均不冒充整题墙钟耗时。
- 输入 2980901 token（缓存 2743440），输出 23813；推理 token 已报告部分 12157，覆盖 63/64 请求。
- 文档搜索 1 次、阅读 1 次，返回 3819 字符；费用未报告。
- 10 次原生执行的输入/命令/退出/产物/释放凭据均复核；4 个已保存验收对象重放完全一致。
  第 5 份有效报告是上述单列审计，不虚构成原控制器已经验收过。

末轮证据：
[第 38 次返回](../runs/tutorial-science-matrix-001/trials/s-102/codex/run/turns/000038/result.json)、
[第 10 次原生输出](../runs/tutorial-science-matrix-001/trials/s-102/codex/run/results/r-000010/run.json)。

## s-102 / FoamClaw：发现验收器误报；两份已提交报告仍有独立数值偏差

旧版本记录：64 次模型 API 调用、42 次 harness 返回、5 次运行提交、35 次提交
格式失败、2 次报告验收失败、0 个基础设施事件，最终 model_budget_exhausted。
最后一次返回 submitted=true 但缺少 action；它不是上述 Codex 末轮报告误分类的同一情形。

| 原生提交 | 实际结果 | 可定位的原因 |
|---|---|---|
| r-000001 | input_validation 失败，未运行 | unclosed comment |
| r-000002 | startup 失败 | 缺 div((nuEff*dev2(T(grad(U))))) 项 |
| r-000003 | 原生完成 | 两份正式报告均引用此运行 |
| r-000004 | 原生完成 | 不冒充已经提交并验收的报告 |
| r-000005 | 原生完成 | 不冒充已经提交并验收的报告 |

旧验收对 r-000002～r-000005 都报了四项物理违反：U/p 的 AMI1/AMI2。
实际边界差异仅为在 cyclicAMI 中增加 `value $internalField;`，p 的
`useImplicit true` 等约束仍保持。不能把这四项当作改变物理边界条件。

v2306 的 cyclicAMIFvPatchField 构造函数将可选 value 用作初始值；后续
coupledFvPatchField::evaluate 由两侧内部场更新耦合边界值。
本地源码和原始归档中 cyclicAMIFvPatchField.C 的 SHA256 均为
`f2a91c7ca2971d14d1d25a075dd48f8ae314673c0af71451590d4231a6584dbe`。
在相同独立原生环境做了一次单变量对照：仅给原始算例 U/p 的两侧 AMI 增加
该初始化值，其余字节不变；最终全部 24 个单元的 U、p 与已有原参考逐项完全相同，
relative L2 和 Linf 都为 0。没有重新运行原参考或调用模型。该作业 7941375
已释放，并独立查询确认不在活动队列。

证据：[单变量原生对照](../runs/ami-initial-value-control-001/assessment.json)、
[独立退出、日志和产物凭据](../runs/ami-initial-value-control-001/native/runs/r-000001/)。

| 原报告 | 原始 task_contract | 修复逻辑只读复核 | U / p relative L2 | 对现有报告的结论 |
|---|---|---|---|---|
| turn 000013，r-000003 | 错误地 false | true | 0.399096 / 0.669875 | 仍未通过场误差验收 |
| turn 000023，r-000003 | 错误地 false | true | 0.399096 / 0.669875 | 仍未通过场误差验收 |

两份报告与真实产物一致，问题不是伪造数据。修复不改变 U 0.10、p 0.15 的 L2
上限，也不改变其他物理约束。**但不能推断模型在正确反馈下仍会失败**：错误反馈
已进入后续轨迹，只读重判无法还原反事实行为，因此本试验标为反馈受影响待重测。

报告证据：[turn 000013](../runs/tutorial-science-matrix-001/trials/s-102/foamclaw/run/evaluations/000013/result.json)、
[turn 000023](../runs/tutorial-science-matrix-001/trials/s-102/foamclaw/run/evaluations/000023/result.json)。

## s-102 / Claude Code：维护中断，不是模型答题失败

确认 AMI 缺陷时，下一试验已发送 1 次 API 请求，尚未提交配置。协作中断控制器后，
客户端收到清理信号，exit=-9、interrupted=true；宿主随后仍收到了上游 HTTP 200
响应，耗时 319.514 秒。给已退出客户端传输时产生 BrokenPipeError，凭据明确
known_response=true。它是此次维护中断的结果，不能称为上游拒绝或模型答错。

引擎 model_calls 尚未提交计数而为 0；实际已发送请求为 1，应以 API dispatch/
complete 凭据补充审计，不能把费用统计为零。没有自动重发。
控制器记录为 interrupted/KeyboardInterrupt，20 题注册清单原样保留。
再次付费运行必须使用新冻结版本和明确的新批次，不能把旧试验标成未调用过。
