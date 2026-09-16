# 修复版 002：付费重测与审阅

**终局更新：**20 项现已全部结束；以下“运行中/排队”段落是带时间的历史快照。
当前结果和最后两项故障见[终局审阅](SCIENCE_MATRIX_002_FINAL_REVIEW.md)。
兼容等修复已在批次结束后部署，部署后测试/新原生资格见[发布记录](SCIENCE_RELEASE_006.md)。

用户已明确确认“开始重测”。本批次为 5 道从零建模题 × 4 个真实 harness，
统一 Kimi-K3、断网、同一固定只读 OpenFOAM 文档、串行。
每题累计最多 64 次模型 API 调用，包含客户端辅助调用；原生累计 600 秒、
每次原生运行 120 秒、单次 API 网络等待 600 秒。未新增单次输出 token 上限。
这是固定模型的 harness 对比，不是 GPT / Claude / Kimi 模型之间的排名。

审计提示（2026-09-12 21:59 UTC）：已发现两项静态检查兼容性缺陷：`latestTime`
错误要求未使用的 startTime；RAS 只识别旧键 RASModel，不认识 v2306 的 model。
后者已造成 s-103 / Codex 的真实合格报告被拒绝。尚未修改活动批次的代码或原始
成绩；候选修正与真实报告复核单列，不能将原表宣称为“无验收器缺陷”的最终排名。
另发现 FoamClaw 默认子目录提示与根部输入采集之间的协议歧义，见 s-103 / FoamClaw
专项记录；相关调用效率也不能直接解释成纯粹的 OpenFOAM 能力差异。

## 最新审阅摘要（2026-09-13 03:49 UTC；不是最终排名）

20 项中已有 18 项结束，1 项运行、1 项排队。原始生命周期为 completed=14、
interrupted=4；原始验收为 5 pass、9 fail、4 error，不能漏掉中断分母。
按证据审阅，这 18 项分别是：5 原始通过、6 工作流未完成（含目录协议歧义）、
2 正式报告的数值场未达标、3 在得到可评分报告前的 API 中断，以及 2 验收器误拒。
后两项分别是 s-103 / Codex 和 s-104 / Kimi Code，首报告候选复核通过；这是审阅
分类，不覆盖原始 fail/error。Kimi 在误拒后的后续请求又发生超时，两个问题不能混成一个。

活动项为 s-105 / Claude Code：4 次 API 已启动、3 已知响应，无 API 告警；
仍在首轮客户端会话，状态提交调用数为 0，无原生提交。Codex 本题已耗尽 64 次
预算结束；FoamClaw 第 2 次响应已知截断后中断。两者均由原控制器自动收尾并推进。
请求进行中的实时计数与按完整客户端轮次提交的状态计数可能不同，不应将差额当作丢失调用。
原控制器 PID/启动标识和冻结源码仍一致，没有重启或重复开批次。

| 题目 | Codex | FoamClaw controlled | Claude Code | Kimi Code |
|---|---|---|---|---|
| s-101 | 通过；15 API | 通过；29 API | 通过；41 API | 通过；18 API |
| s-102 | API ReadTimeout 中断；12 API，无原生提交 | 预算失败；64 API，2 次原生提交 | 预算失败；64 API，3 次原生提交 | 预算失败；64 API，6 次原生提交 |
| s-103 | 原记录预算失败；第 33 次 API 的真实首报告经兼容修复候选复核通过 | 64 API、0 原生提交；目录/格式协议问题，不能判为物理错误 | 64 API、4 次原生提交；最终全场通过，但未提交报告，预算失败 | 64 API、8 次原生提交；两份正式报告均仅压力全场超阈值，预算失败 |
| s-104 | 通过；61 API、8 次运行、2 份报告；首报告把计算耗时当成仿真时间，随后自行修正 | 已知输出截断中断；1 API、0 原生提交，原状态原因误标为结果不明 | 预算失败；64 API 中仅 10 次主解题；19 次查文档，0 原生提交、0 报告 | 第 18 次 API 的首报告被静态检查误拒，候选通过；误反馈后第 28 笔 API 超时，原记录 error |
| s-105 | 预算失败；64 API、10 次原生、5 份报告均数值未达标 | 已知截断中断；2 API、0 原生提交 | 运行中；首轮会话，3 已知 API | 排队 |

s-102 三个非中断试验都曾跑完，但均未交出合规后处理报告；事后已有场诊断也
未通过固定离散基准，Kimi Code 的速度已达约 10¹⁹ m/s，不能将退出 0 当作物理通过。
这些是固定 Kimi-K3 的 harness 工作流结果，不是三个不同模型的能力排名。
Claude Code 的 64 次调用中仅 25 次为主解题会话，39 次为客户端预热/辅助分析。

兼容修复候选仍未部署，114 项静态测试全部通过。早期只读影响审计覆盖 29 份
原生结果与 8 份正式 evaluation：s-103 / Codex 的三份真实报告由 fail 变为候选 pass。
首报告 turn 000009 出现在错误评分反馈之前，可独立确认模型已完成题目；第二份及
后续动作受错误反馈影响，不能当作一段全新的公平轨迹。原始报告失败次数不能直接
解释为物理错误次数，原表与修正审计必须并列阅读。

兼容修复候选另通过 61 项既有回归（公开约束、全场比较、报告防伪、安全、AMI），
0 失败/跳过/外部动作尝试。[测试记录](../review_candidates/v2306_compat_v1/existing-regressions-001.json)
与 114 项新边界测试分列；这不是完整 536 项回归，也不是正式部署资格。

目录协议候选另外完成 49 项单元测试及四个真实客户端的两轮提交/恢复测试，
全部通过；后者为 28 次本地假 API 请求，付费请求和原生命令均为 0。
[接口测试及两次测试脚本误判复盘](../review_candidates/workspace_contract_v1/README.md)
保留所有失败记录。候选尚未部署，不能将接口通过等同于模型完成物理题。

新发现 s-103 / Claude Code 一次本地文档查询超时：单线程 broker 会让只读文档
排在模型请求后面。无费用复现还证明，宿主保存文档 HTTP 200 不等于客户端收到。
现有 returned_characters 只能代表生成的响应字符，不能代表全部进入模型上下文。
[源码、复现和待修边界](../review_candidates/docs_concurrency_v1/README.md)。
独立文档服务及统计接线候选现已通过 38 项本地边界/恢复/报表测试、四个真实
客户端的查阅/恢复/统计测试，以及 11 个已结束真实试验的历史报表兼容核验。
客户端测试仅使用本地假模型；历史核验只在数据库快照上生成报表，原始成绩、
API/token/费用统计保持不变，旧记录的文档传输一律保留 unknown。
正式部署与新原生资格仍未完成，未修订活动批次或启动付费补测。

三项修复现已组合到独立代码副本，并通过原项目完整 **536 项回归，0 失败、0 跳过**，
含 42 项真实 namespace / 客户端本地假 API 测试。五题协议身份与候选接线核验通过。
[组合代码结构、全部测试及前序失败复盘](../review_candidates/integrated_release_v1/README.md)。
这补齐了组合回归，不等于正式部署或新原生资格；生产源码与原成绩仍未变。

随后发布接线审阅发现 build-002 的 factory/批次身份缺少实例已声明的文档传输
版本，属于尚未部署候选的缺口，不是当前模型错误的原因。新增测试在旧副本出现
16 项失败，统一身份生成函数后 28 项全部通过；build-003 随后完整 **564 项全部通过，
0 失败、0 跳过**。候选仍未部署，不混用两种身份继续当前会话。
组合副本最新重放了全部 11 份已保存真实报告，只有 s-103 / Codex 的同题三份报告
发生兼容修正，数值距离和报告忠实性没有变化，未替未交报告的试验补分。
新增 s-104 / Codex 的两份报告仍分别 fail、pass，候选没有放过错误时间值。
[最新只读重放记录](../review_candidates/integrated_release_v1/build-003/replay-002/summary.json)。

新增 s-104 / FoamClaw 的已知截断分类缺陷已在独立候选修复，未部署：先持久化
明确的已知/未知结果及调用用量，恢复时只回收凭据、不重发或重复计数；残缺工具
调用不会被执行。53 项定向测试通过后，build-004 完整 **617 项通过、0 失败/跳过**，
无付费或原生执行，候选和生产源码未变。见
[具体代码路径、真实记录复核和测试证据](../review_candidates/provider_outcome_v1/README.md)。
同一 build-004 重放 11 份真实报告，仍只有 s-103 / Codex 三份因兼容修复改变，
没有放宽数值阈值、篡改旧成绩或替未交报告者补分。正式部署及新原生资格仍待完成。

随后发现“显式写出默认 kEpsilon 系数也被拒绝”的边界。独立 build-005 已通过
108 项定向测试，完整 **725 项回归全部通过、0 失败/跳过，442.20 秒**；
[来源、边界和验证记录](../review_candidates/default_coefficients_v1/README.md)。
四真实客户端本地假 API 测试启用，生产源码未变，没有新付费或原生执行。
该副本首次重放 12 份真实报告，新增 s-104 / Kimi Code 的首报告候选通过；
随后重放增至 13 份，Kimi 同题第二份报告也候选通过，但它已受错误反馈影响。
因此“只有 s-103 发生修正”仅描述前述 build-004/11 份报告的历史快照，不是当前结论。

下面保留逐题过程和历史快照；即时进度以[控制器实时表](../runs/tutorial-science-matrix-002/scoreboard.md)为准。

## s-104 / Kimi Code：误拒后的超时与本地退避，不是额外付费重发

[终态请求/进程/原始分数审计](../runs/tutorial-science-matrix-002/trials/s-104/kimi-code/review/terminal-timeout-001.json)：
28 次上游请求中 27 次 HTTP 200，第 28 次约 600.30 秒后保存 ReadTimeout，
known_response=false、没有 complete/raw 响应。六次客户端启动均已退出，最后退出码 1，
不是外层客户端 watchdog 杀死；原控制器自动进入下一项。

本地错误原文为 `503 Previous request failed; host review required, no automatic redispatch`。
Kimi 客户端记录 9 次退避事件（失败尝试 1–9，最大 10），声明等待合计 **144.47 秒**。
这些请求被本地 broker 拒绝，没有新增上游 dispatch；不能称为额外 9 次付费调用。
根因是已锁止转发却返回可重试 503。另有桥接 socket 的 BrokenPipeError，说明客户端
连接已断开，不能将它解释成 OpenFOAM 或模型物理错误。

原始总量：模型阶段 2955.44 秒，原生 166.93 秒，3 次原生、2 份报告、0 格式失败；
已知用量覆盖 27/28，输入 1,261,721、输出 29,714、合计 1,291,435 token，费用未知。
首报告第 18 次调用时已经数值合格；其后轨迹受误反馈影响。候选复核与原 error 并列，
不利用后续超时否定首报告，也不伪造一次新 pass 或独立样本。

对应候选在 build-005 上先复现 **21/21 失败**；build-006 修正本地终态状态后，
新增 **33/33 测试通过**，含四真实客户端的本地假 API，0 付费/原生执行。
随后[完整回归](../review_candidates/integrated_release_v1/build-006/tests-002/summary.json)
**758 项全部通过，0 失败/跳过，480.72 秒**，包括上述 33 项；候选和生产源码未变。
只改本地终态，不改上游原始状态/用量、不重发、不加输出上限；
详见[失败状态修复和证据](../review_candidates/provider_outcome_v1/README.md)。尚未部署。

## s-105 / Codex：首报告的 U/s 场偏差

### 已结束的完整统计

[10 次原生与 5 份报告逐项核验](../runs/tutorial-science-matrix-002/trials/s-105/codex/review/verified-001.json)
及 [64 笔请求、20 次客户端退出、预算边界核验](../runs/tutorial-science-matrix-002/trials/s-105/codex/review/completion-001.json)
均已完成：原始记录保持不变。该题不是 API 错误终止。
[候选的终局只读重放](../review_candidates/integrated_release_v1/build-006/replay-003/summary.json)
覆盖全批当时 18 份真实报告，确认这题的五份新旧均 fail，未放宽数值判据。

| 项目 | 终局 |
|---|---|
| 模型请求 | 64/64 HTTP 200、Kimi-K3；0 API 错误、0 截断；请求未加输出上限 |
| 客户端返回 | 20 轮；记录 PID 均已退出；末轮因已知预算停止退出 1，但有效的新 run 提交仍获执行 |
| 原生提交 | 10 次：5 完成、4 数值发散（SIGFPE）、1 首步配置错误 |
| 正式报告 | 5 份全部提取忠实、静态约束/场合法性通过；整体数值验收 0/5 |
| 格式失败 | 5 次均未产生新的 action 文件，不是 API 返回空文本或损坏 JSON |
| 工作区命令 | 47 次记录，3 次非零退出：向量解析、残差尾逗号解析、读取已消费的 action |
| Agent 阶段 / 原生耗时 | 2486.23 秒 / 77.10 秒；前者包含 API 与客户端/工具过程，不是纯模型生成时间 |
| 已知 token | 输入 3,976,131；输出 29,642；总计 4,005,773；cache 字段 2,816,709 |
| reasoning / 费用 | reasoning 字段 17,457，覆盖 62/64；费用无上游记录，不能推算为零 |
| 文档 | 7 搜索、2 读取，生成响应 18,835 字符；不等同于全部进入模型上下文 |

五个缺提交轮次是 2、5、7、8、19：上游正常返回 `stop` 和非空说明文字，
没有末尾结构化工具调用，也没有新的 system/science-action.json。
例如第 2 轮以 “Let me fix it.” 结束，却尚未做修正。原日志的
`Expecting value: line 1 column 1 (char 0)` 实际来自缺 action 的空输入解析，
不能描述为它提交了一份语法错误 JSON。显式根目录/提交契约候选尚未部署，
也不能仅凭这些记录认定提前停止来自模型、harness 或上下文管理的哪一层。

最后 r-000010 同时收紧求解容差并删除 pFinal / `(U|k|epsilon|s)Final` 条目，
OpenFOAM 报 `Entry 'UFinal' not found in dictionary "system/fvSolution.solvers"`。
这是首次时间步尚未完成的配置错误（原 stage=startup），不是物理场误差，也不是
先前已修的 verifier 静态兼容误拒。末轮有效提交已在 API 预算边界执行，没有被丢弃。

第 19 轮说明还把早先速度格式回忆成 plain upwind，但 r-000001 实际是 linearUpwind；
这是自述与操作轨迹的不一致，不据此断言完整隐藏 reasoning 或具体记忆机制出了什么问题。

截至上述快照：r-000001 正常完成，原生 12.12 秒；第 21 次 API 后首报告
turn 000003，静态约束、原生完成、场合法性、报告忠实性均通过。
相对 L2：U=0.154332（阈值 0.10）、s=0.161322（阈值 0.10），两项失败；
p=0.143878（0.15），k=0.173148、epsilon=0.231437、nut=0.143097（均 0.25），通过。
报告无提取值不一致。这是当前未结束试验的首报告，不是最终能力分数。

后续 r-000002 仅改 fvSchemes：速度从 linearUpwind 改为 linear，k/epsilon 从 upwind
改为 limitedLinear 1；1.65 秒后数值发散，残差上升至约 10⁸，触发 sigFpe。
r-000003 也为原生 numerical 失败，1.81 秒。这些运行失败保留，既不改记格式异常，
也不以首轮能跑完替代最终物理场验收。原生日志与输入快照均在对应 trial/native/runs/。

r-000004 再次运行完成（12.25 秒），第 39 次 API 后的第二份报告 turn 000010
仍仅 U/s 场失败：relative L2 分别 0.154331562、0.161321900；其余四场及报告忠实性通过。
r-000005 执行失败（2.37 秒），r-000006 随后完成（16.11 秒）。
第 48 次 API 的第三份报告 turn 000013 仍仅 U/s 不达标。

### 数值复现失败不等于物理意图理解错误

公开题面允许选择求解器、松弛与离散格式，但同时明确固定离散参考及全场阈值，
并未承诺任意可运行格式都通过。现有结果符合这条判分协议；不能据此进一步证明
模型误解了边界、湍流模型或标量源，也不能反过来证明其结果是正确的连续物理解。
本任务没有网格收敛/实验真值，数值误差来源尚未用专门的单变量原生实验排除。

前三份真实报告对应 r-000001、r-000004、r-000006，静态物理约束、原生完成、
场合法性与后处理忠实性均通过。下面列实际字典中的离散选择，不向受测模型反馈：

| 项目 | 隐藏原参考 | 首份完成输入 r-000001 |
|---|---|---|
| div(phi,U) | Gauss limitedLinearV 1 | Gauss linearUpwind grad(U) |
| div(phi,k)、div(phi,epsilon) | Gauss limitedLinear 1 | Gauss upwind |
| div(phi,s) | Gauss limitedLinear 1 | Gauss upwind |
| p / U 绝对求解容差 | 1e-6 / 1e-5 | 1e-7 / 1e-7 |

r-000004 相比首份仅在 fvSchemes 的 k/epsilon upwind 前加 bounded；
r-000006 相比首份仅改 fvSolution，收紧容差并增加压力校正次数。
后者 U/s relative L2 仍为 0.154331833 / 0.161323718，几乎未动。
这是“单纯收紧线性求解并未消除偏差”的已观察证据，**不是已证明对流格式是唯一原因**。

第四份报告 turn 000015（53 API）对应 r-000007，正常运行 13.56 秒。
相对 r-000006 仅改 fvSchemes，把 U/k/epsilon/s 的对流全部换成 bounded Gauss upwind。
U relative L2 降至 0.097024840，通过；s=0.103231361，略超 0.10；
p=0.287847679、k=0.471052264、epsilon=0.606120469、nut=0.288941450，均超过各自阈值。
只看一个场改善会误判整体进展，六场及失败运行都保留。

[build-006 第二次只读重放](../review_candidates/integrated_release_v1/build-006/replay-002/summary.json)
覆盖当时全部 17 份真实报告，包含这里的四份；新旧验收对这四份均判 fail，
数值与后处理检查未变。仍仅修正前述 s-103/Codex、s-104/Kimi Code 的静态误拒。
原始输入证据在 [r-000001](../runs/tutorial-science-matrix-002/trials/s-105/codex/native/runs/r-000001/inputs.json)、
[r-000004](../runs/tutorial-science-matrix-002/trials/s-105/codex/native/runs/r-000004/inputs.json)、
[r-000006](../runs/tutorial-science-matrix-002/trials/s-105/codex/native/runs/r-000006/inputs.json)、
[r-000007](../runs/tutorial-science-matrix-002/trials/s-105/codex/native/runs/r-000007/inputs.json)。

发布准备另完成三道 RAS 题的显式默认系数单变量控制登记，
[私有输入与门禁](../review_candidates/integrated_release_v1/build-006/default-controls-001/preregistration.json)
保留原判据；[7 项生成器检查](../review_candidates/integrated_release_v1/build-006/default-controls-001/preparation-tests.json)
通过，无付费/原生执行。它们尚未运行，不计入模型结果或正式原生资格。

## s-105 / FoamClaw：第二笔响应已知截断，尚无原生提交或可评分报告

[原始响应元数据与终态审计](../runs/tutorial-science-matrix-002/trials/s-105/foamclaw/review/truncation-diagnosis-001.json)：
第一笔 HTTP 200、1 次结构化工具调用，107.71 秒；第二笔 HTTP 200，159.70 秒，
finish_reason=length，8192 个 completion token 全部报告为 reasoning，正文和工具调用为空。
两笔均 Kimi-K3；发送请求未包含 max_tokens/max_output_tokens/max_completion_tokens。
它再次暴露上游已知截断与原状态误分类，不证明所有请求都使用统一 8192 上限。

原始模型阶段 268.96 秒，2 API、0 原生、0 正式报告、0 格式失败；输入 9960、
输出 8285、总计 18245 token，用量覆盖 2/2，费用未知。客户端退出 1、非 watchdog
超时，记录 PID 已退出。原 reason=model_request_outcome_unresolved 保留；
build-006 的只读分类为 known / provider_output_truncated，observed_requests=2、
known_responses=2、automatic_retry=false。不把 reasoning 内容改造为正文或伪造提交。

分类修正不能消除上游自身截断；没有修改当前输出参数，也没有付费重试。

## s-104 / Kimi Code：首份正式报告满足数值要求，静态验收误拒

首报告 turn 000003、累计 18 次 API（前三轮 10+4+4），没有此前报告评分反馈。
全部 18 笔均为 Kimi-K3 / HTTP 200、无 API 异常、无截断、无格式失败。
截至这份报告，模型耗时 1457.290 秒、原生累计 82.616 秒；不使用后续错误反馈后的
累计成本替代这个干净前缀，也不把后续尝试作为独立采样。

第一次运行 blockMesh/checkMesh 通过，但 pimpleFoam 第 2 轮 PIMPLE 读取 UFinal
时报缺项。原表 numerical 是发生阶段，不代表数值发散。模型第二次仅修改
system/fvSolution，补 UFinal、kFinal、epsilonFinal；其他输入包括物性和系数未变。
第二次耗时 81.189 秒，完成 1204 个时间步至 0.3 s，正常 End。两项作业 7941807、
7941815 的释放凭据已核验，均已离开独立查询的调度队列。

| 首报告检查 | 实际结果 |
|---|---|
| 原生完成、场非负性 | 通过 |
| U 相对 L2 误差 | 0.0005046414；通过 |
| p 相对 L2 误差 | 0.0010503316；通过 |
| k 相对 L2 误差 | 0.0012385430；通过 |
| epsilon 相对 L2 误差 | 0.0032098591；通过 |
| nut 相对 L2 误差 | 0.0010482454；通过 |
| 五场相对 Linf | 全部通过 |
| 报告与原生产物逐项核对 | 全部通过，无伪造或时间值错误 |
| 原静态检查 | 误拒 v2306 的 model 键 |
| build-004 静态检查 | 识别 model，但误拒显式默认系数字典 |
| build-005 候选复核 | 全部通过；阈值、全场距离与报告核对均未修改 |

Kimi 写的 Cmu=0.09、C1=1.44、C2=1.92、sigmaEps=1.3 与固定源码默认值相同；
原生日志还打印 C3=0、sigmak=1，六个有效值均为默认。不能把“显式写出默认值”
称为实际改变物理模型。本轮不修改旧验收结果；新增候选和新原生资格单列。
首次原生反馈只含清理后的实际错误，没有把私有静态差异泄漏给模型。

首报告前用量：input=713253、output=21677、total=734930、cached_input=555114、
reported_reasoning=12827；实际费用未知。文档 5 次搜索、2 次读取，生成字符 13589；
这个生成字符统计不单独证明模型接收或理解。

[首报告、两次输入差异、时间步与干净前缀审计](../runs/tutorial-science-matrix-002/trials/s-104/kimi-code/review/first-report-001.json)、
[原生错误及固定源码默认值证据](../runs/tutorial-science-matrix-002/trials/s-104/kimi-code/review/native-prefix-001.json)、
[原版/候选逐项验收对照](../review_candidates/integrated_release_v1/build-005/replay-001/s-104/kimi-code/report-000003.json)。
这份真实报告由受测模型提交；审阅没有补造报告或重新运行算例。当前控制器仍按
冻结策略继续，尚无该试验终局结论；后续结果必须标明受错误反馈影响。

后续 r-000003 在 84.312 秒内再次完成 1204 步至 0.3 s。模型只删除显式
kEpsilonCoeffs，并把 convertToMeters=1 换成 scale=1；五个最终场文件与 r-000002
逐字节相同。第 25 次 API 的第二份正式报告仍仅被旧静态检查拒绝，候选复核通过。
这是两项语法变化后的既有运行，不冒充预登记的单变量资格对照，也不是独立采样。
[实际 diff、五场哈希与第二份报告对照](../runs/tutorial-science-matrix-002/trials/s-104/kimi-code/review/native-prefix-002.json)。
第三个作业 7941824 已记录释放，独立队列查询也已确认其不在队列。

## s-104 / Claude Code：检索后预算耗尽，没有配置或物理提交

终局 completed/fail、model_budget_exhausted。64 次 API 全部 HTTP 200 / Kimi-K3，
0 API 异常、0 输出截断；一次客户端调用累计 2513.632 秒，原生耗时为 0。
客户端 exit=1、未超时，已记录 PID 不在宿主 /proc；控制器已继续 Kimi Code。

| 请求类别 | 次数 | 已记录上游响应耗时（秒） |
|---|---:|---:|
| 主解题会话 | 10 | 659.093 |
| 客户端 specialist 预热 | 3 | 38.384 |
| 客户端路径提取 | 18 | 881.460 |
| 客户端命令前缀分析 | 33 | 923.369 |

54/64（84.375%）是客户端辅助调用，按冻结协议也计入总预算；这不是 64 次完整
解题轮次。不能据此断言“换成 64 次主会话一定成功”，也不在运行中改变分母或预算。
这些耗时是已知响应的记录总和，不等于一个独立硬件性能试验或真实费用。

实际 20 条 Bash 工具结果为：1 次列目录、12 次文档搜索、7 次文档阅读。
没有写入算例配置的工具命令，最终采集输入为空、没有 action、没有原生提交或报告。
原表的 1 次 format_failure 是“没有提交 action”，不是提交了 JSON 后解析出错，
更不是 OpenFOAM 语法错误或物理场不合格。

文档并未在本次超时：19 份宿主响应正文与 19 份客户端工具输出逐份解析后完全相同。
其中 17 份还在后续已发起请求的对应 tool_call_id 中找到相同正文；最后两份结果
虽已返回客户端，但预算耗尽前没有再发给主解题会话。输出存在、发出请求与模型
真正理解是三个不同层次，不把 returned_characters=44503 当作全部被理解的证据。

内容也有局限：实际读到的 blockMesh 正文 708 字符，PIMPLE 正文仅 58 字符且标记
underConstruction；multiGrading 的单词搜索结果为 0。本记录只说明这次检索获得了
什么，不证明整个文档库完备、也不单凭此推断检索导致失败。冻结文档本轮不改。

用量：input=349810、output=28125、total=377935、cached_input=116247；
reported_reasoning=25625，64 笔均有对应字段，实际费用未知。
本题没有物理答案可以评分，单列为工作流未完成，不计作通过或物理错误。

[终局、工具与用量凭据](../runs/tutorial-science-matrix-002/trials/s-104/claude-code/review/verified-001.json)
及[64 笔请求分类、逐份文档交付/后续请求证据和退出边界](../runs/tutorial-science-matrix-002/trials/s-104/claude-code/review/completion-diagnosis-001.json)
均只读核验；没有补写模型报告、重发请求或新增原生执行。

## s-104 / FoamClaw：首请求已知截断，未进行物理作答

第 1 次请求 HTTP 200，耗时 260.044 秒，finish_reason=length；
output=8192 token、reported_reasoning=8192，正文 0 字符、没有工具调用。
请求没有 max_tokens/max_completion_tokens/max_output_tokens，不是本框架在这次
请求中加入了 8192 上限；单次观测也不能证明中转平台所有请求的默认上限相同。

适配器先报 Provider returned neither text nor tool calls，错误凭据明确
known_response=true；引擎却统一记录 model_request_outcome_unresolved。
这是“已知截断”与“真正请求结果不明”的程序性分类矛盾，原记录保留不覆盖。
该试验 interrupted/error、1 API、0 原生提交、0 正式报告，不能算物理失败。
客户端 exit=1、未超时，PID 已消失；控制器继续 s-104 / Claude Code，未自动重发。

token：input=5218、output=8192、total=13410、cached_input=0，实际费用未知。
reasoning 原文仅保存在原始受限轨迹，此处没有把它展示为完整思维链或可靠解释。
[原始请求/响应哈希、已知状态矛盾与用量审计](../runs/tutorial-science-matrix-002/trials/s-104/foamclaw/review/truncation-diagnosis-001.json)。
终态分类候选现已完成本地接口/恢复测试并通过组合完整回归，仍未部署；
不改变活动批次的参数、token 上限或重试政策。解析器修复本身不能消除上游输出截断。

## s-104 / Codex：最终通过，首份报告失败后自行修正

终局 completed/pass、quantitative_acceptance。61 次 API、15 次 harness 返回、
8 次原生运行、2 份正式报告；模型耗时 3001.480 秒，原生累计 331.826 秒。
全部 61 次请求均为 Kimi-K3、HTTP 200，0 API 异常、0 输出截断；
15 个客户端的退出凭据已核验，宿主查询确认对应 PID 均已消失。

| 检查项 | 首份报告（累计 58 API） | 第二份报告（累计 61 API） |
|---|---|---|
| 原生完成、公开配置、场非负性 | 通过 | 通过 |
| U / p / k / epsilon / nut 全场 | 全部通过 | 全部通过，使用同一 r-000008 |
| final_time 自报值 | 66 秒，错误地取了 ClockTime | 0.3 秒，与仿真结果一致 |
| 其他自报测量值 | 全部匹配 | 完全未变，全部匹配 |
| 正式验收 | fail，仅 final_time 不匹配 | pass |

模型后处理使用未限定行首的 Time 正则，误匹配日志末尾的 ClockTime=66；
真实 Time=0.3，公开题面也要求从零推进至 0.3 秒。这个失败不是物理场错误，
也不是静态兼容误拒。模型在收到允许的字段不匹配反馈后，用 3 次额外 API
修正报告；没有新求解、没有由审阅者代写报告。首次报告成功=false，最终成功=true。

五场 relative L2：U=0.00590205、p=0.03089363、k=0.02228387、
epsilon=0.03365108、nut=0.03754660，均在预登记阈值内；Linf 也全部通过。
运行过程保留 3 次字典错误、2 次原生预算耗尽、2 次数值发散、1 次完整运行成功。
另有 5 次缺 action、1 次正式报告失败，不能混为 6 次物理错误。

48 条实际命令结果中有 4 条非零退出：文档页请求 size=20000 超过允许的 16000、
读取已消费的 action 文件失败、后处理 shell 引号错误、向量解析误当标量。
这与 API 状态和 OpenFOAM 运行失败分别统计。文档为 6 次搜索、1 次成功 read、
1 次请求拒绝，12113 个生成字符；旧凭据不证明文本已送达客户端。

token：input=3,299,319、output=39,322、cached_input=2,129,792、
reported_reasoning=22,618、total=3,338,641；实际费用未知。

- [八次原生证据、两份验收重放、命令错误和用量](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/verified-001.json)。
- [61 次请求、15 个退出进程、五次缺 action 与实际报告自纠错](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/completion-diagnosis-001.json)。
- [真实首报告及兼容候选对照](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/first-report-001.json)。
- [模型后处理正则、Time/ClockTime 日志及独立核验](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/report-time-diagnosis-001.json)。

### 以下保留运行时的过程记录（终局以上文为准）

前两次提交合计 15 次 API（首轮 13、第二轮 2），两次都真实执行了网格、网格检查
与求解器；不是同一输入被重复提交。原生累计耗时 4.145 秒。

| 提交 | OpenFOAM 原文 | 模型后续修改 |
|---|---|---|
| r-000001 | Residual data for U must be specified as a dictionary | 把 PIMPLE/residualControl 内 U、p、(k\|epsilon) 的标量改为含 tolerance、relTol 的字典 |
| r-000002 | Entry 'pFinal' not found in dictionary "system/fvSolution.solvers" | 添加 pFinal，同时修改压力求解容差、光滑器及 PIMPLE 设置；完整 diff 见下方审计 |

第二次 stage=numerical，但原因是延迟读取时缺 pFinal，不代表已经证明数值发散。
两次 task_contract 都通过只表示预先登记的物理设定约束满足，不能代替 OpenFOAM
完整运行检查。没有正式报告，因此还不能给物理验收结论。
[输入差异、每步退出、原生日志、产物和释放凭据](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/native-prefix-001.json)
仅覆盖这两次已完成运行，不冒充整题终局审计。

00:47 UTC 核验到 33 次 API 均已返回，0 API 告警；6 次原生提交（第六次进行中）、
1 次缺 action、0 正式报告。控制器进程身份及冻结源码均未变化。

| 提交 | 实际结果 | 关键证据 |
|---|---|---|
| r-000003 | 缺 UFinal；1.590 秒 | Entry 'UFinal' not found in dictionary "system/fvSolution.solvers"；首个时间步第 10 轮 PIMPLE 才触发读取，仍是字典错误 |
| r-000004 | 达到单次 120 秒原生限额 | 求解器 timed_out=true、exit=-9；最后完整时间步 0.034964 s，随后开始 0.035064 s，但未完成；目标为 0.3 s |
| r-000005 | 真实数值发散；9.482 秒 | 最大已记录 Courant 数约 1.50e83，epsilon 到约 6.48e106，随后 sigFpe / GAMGSolver 栈退出 |

r-000004 已补齐 UFinal/kFinal/epsilonFinal。模型设置 maxDeltaT=0.0001、
nOuterCorrectors=25；实际完成 357 个时间步，每步外迭代 8–16 轮，中位数 10，
没有一步达到 25 轮。不能把“上限 25”写成“每一步执行 25”。该次写出间隔为
0.3 s，并非频繁输出造成大量文件。超时是原生运行限额，不是 API 限流。

r-000005 同时把 nOuterCorrectors 改为 1、删除 residualControl 和 maxDeltaT、
初始 deltaT 从 1e-5 改为 1e-4、压力 relTol 从 0.1 改为 0.01，并把写出改为
每 3000 步；这不是单变量试验，不能把发散唯一归因于其中一处。

原始参考的历史准备凭据记录为 64.306 秒完成 1197 个时间步、到达 0.3 s，
实际每步一轮 PIMPLE。它说明本题曾在限额内运行完成，不证明所有合法数值方案
都必然在 120 秒内完成，也不是本轮重新计算或公平硬件性能对照。

[第三至第五次的完整输入 diff、退出、日志统计、产物与释放凭据](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/native-prefix-002.json)
已核对；作业 7941758、7941759、7941762 均已离开独立查询的队列。

另一次工作流错误发生在 harness 第 5 轮：客户端正常结束，3 条实际命令均退出 0，
但没有重新写 system/science-action.json，故旧反馈出现 Expecting value。
这里的“格式失败”不是空 API 响应或物理报告失败；候选公共路径反馈修复仍未部署。
[本轮缺 action 的原始边界和命令凭据](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/format-diagnosis-001.json)。
此时没有正式报告，不由审阅者生成报告来补记成功。

后续核验：r-000006 仍触达 120 秒原生限额，但已完成 934 个时间步，最后完整
时刻为 0.231576 s；0.23183 s 只是最后启动的时间步，尚未到目标 0.3 s。
模型改为 3 轮 PIMPLE、增加压力松弛 0.3、恢复 residualControl、把 maxDeltaT
设为 0.01，并恢复最终时刻写出；这次没有重现前次的极端发散，但也没有完成。
[第六次实际 diff 和完整原生证据](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/native-prefix-003.json)。
此后快照为 35 次 API 已启动、34 次结果已知，0 API 告警；格式失败累计 2 次，
尚无正式报告。继续由原控制器执行，不改运行时限。

第 2 次格式失败也已审阅：harness 第 8 轮只调用 API 一次，HTTP 200、
finish_reason=stop，返回 218 字符的普通叙述，没有 structured tool_calls。
客户端因此正常结束，本轮实际执行命令数为 0，也没有重写 action 文件。
这不是空文本、输出截断或适配器丢弃已有工具调用；不能把“将检查产物”的文字
当作已经提交了检查命令。原响应与边界哈希见
[第二次缺 action 审计](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/format-diagnosis-002.json)。

r-000007 在累计 44 次已返回 API 后执行，9.312 秒即再次数值发散，最大已记录
Courant 数为 1.2013e59，最终在 sigFpe / GAMGSolver 栈退出；不是第三次超时。
相对 r-000006，模型将外迭代从 3 改为 1、删除 residualControl 和松弛设置、
把 U/k/epsilon 线性容差收紧为 1e-6 且 relTol=0、压力 relTol 改为 0.05，
还将 controlDict 中 deltaTGrow 的字面值改为 1.05。这里只记录输入变化，
不表示该键已被求解器采用，也不把多项同时修改当作单变量归因证据。
[第七次输入、日志、退出、产物及释放审计](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/native-prefix-004.json)。
七次提交目前为 3 次字典错误、2 次原生预算耗尽、2 次数值发散；尚无正式报告，
任务仍由原控制器继续，不改变已冻结的预算或物理阈值。

**01:03 UTC 新进展：第八次原生提交首次完成。**累计 46 次已返回 API 后提交
r-000008，耗时 67.192 秒，1204 个时间步全部完成并到达 0.3 s，正常 End；
task_contract 通过。此时正发起第 47 次 API，进入后处理，尚无正式报告。
相对 r-000007，仅 fvSolution 变化：外迭代 1→2，p/U/k/epsilon 的 tolerance
放宽到 1e-4、relTol=0.1，并恢复 U/k/epsilon 的 0.7 松弛。实际每步两轮 PIMPLE。
这是一次成功运行，不代表全场误差或报告忠实性已经通过。
[第八次输入与完整原生审计](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/native-prefix-005.json)。

关于前次 deltaTGrow 的修改，另完成只读源码核验：本机六份时间步相关源码与
固定 v2306 归档成员逐字节相同，归档 SHA256 与题库来源登记相同。
pimpleFoam 的该路径读取 adjustTimeStep/maxCo/maxDeltaT，增长因子使用源码中的
阻尼公式及 1.2 上限，并不读取 deltaTGrow。r-000007 虽写 deltaTGrow=1.05，
初始 deltaT=0.0001 后首个实际步长仍为 0.00012，与该判断一致。
这证明这项配置修改无效，不证明它是发散的唯一原因，也没有向模型追加此私有审阅反馈。
[来源哈希、具体源码行及实际日志证据](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/time-step-source-001.json)。

后处理阶段第 11 轮用了 5 次 API：先成功列出 r-000008/0.3 的五个场并读取 U，
随后生成后处理脚本的 shell 命令退出 2，原文为

```text
/usr/bin/bash: -c: line 95: unexpected EOF while looking for matching `"'
```

这一轮末条响应、以及第 12 轮唯一响应，HTTP 均为 200、finish_reason=stop；
内容分别为 116/155 字符，出现“曾调用工具 exec_command”的普通文字，
没有 structured tool_calls。第 12 轮因此没有实际命令执行，两轮均未重写 action。
不能把文字中的命令当作已执行，也不能仅凭原始响应区分模型与上游中间层责任。
[两轮 API、实际命令退出及缺提交边界](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/postprocessing-prefix-001.json)
已单列；截至这两轮，格式失败累计 4 次，仍无正式报告，不替模型补写报告。

还向前追溯了前 52 次已完成请求：“曾调用工具”的字面标记最早出现在第 9 轮
第 10 次 API 的上游响应。在此之前，以及该次的客户端请求和实际出站请求中，
都没有这个字面标记；后续历史则保留了这段既有 assistant 输出。
因此不是我们先把这串标记加入请求，但这不能排除提示/历史安排对行为的影响，
也不能区分模型生成与上游转换。第 9 轮已提前写好 run action，故那次仍提交了
第七次原生运行；有普通文字标记不必然等于本轮完全没有有效提交。
[逐请求哈希与首次出现位置](../runs/tutorial-science-matrix-002/trials/s-104/codex/review/tool-marker-origin-001.json)。

## s-103 / Kimi Code：两份真实报告压力未达标，最终预算失败

终局 completed/fail、model_budget_exhausted。64 API、16 次 harness 返回、8 次原生
提交、2 份正式报告；模型耗时 3665.883 秒，原生耗时 95.706 秒。全部请求均为
HTTP 200、Kimi-K3，0 API 错误、0 输出截断。不能据此把工作流格式问题也说成不存在。

| 原生提交 | 结果 |
|---|---|
| r-000001 | controlDict 缺 deltaT，blockMesh 失败 |
| r-000002 | 缺 blockMeshDict，blockMesh 失败 |
| r-000003 | fvSchemes 缺 div((nuEff*dev2(T(grad(U)))))，求解器启动失败 |
| r-000004 | 缺 ddt(epsilon)，求解器已做首轮 U/p 后才报错；实际仍是字典问题，numerical 只是阶段标签 |
| r-000005、006 | 运行完成；各提交一份数值忠实的报告，但压力 relative L2 约 0.2933，超出 0.15 |
| r-000007、008 | 运行完成，无新正式报告；事后压力 relative L2 分别 0.3751、0.2948，其他四个场通过 |

6 次 format_error 全是根部没有新 action，并非空 API 响应。对应末条上游响应
已有非空文本和“曾调用工具”字样，finish_reason=stop、没有结构化 tool_calls。
因此不能说适配器把已有结构化工具调用吞掉；也不能仅凭这些字样区分是模型生成
还是上游中间层处理。旧反馈只有 JSON 的 Expecting value，公共路径候选用于改进
这一反馈，但不把普通叙述擅自执行成工具调用。

最后一轮用了剩余 15 次调用，实际写好 run action 后触达已知预算。客户端 exit=1，
但无超时/代理错误；末轮 action 恢复规则正确生效，accepted_terminal_action=true，
r-000008 确实执行完毕。没有第三份正式报告，不由审阅者代写来补记成功。

token：input=3,728,547、output=26,140、cached_input=2,639,327、reported_reasoning=14,254、
total=3,754,680。上游一条请求总数少报 7 token，原值保留；实际费用未知。
文档为 2 次搜索、0 次阅读、5574 生成字符，旧记录无传输凭据，不宣称全部已收到。
8 个作业的释放凭据与退出、日志、产物字节已核验，独立队列查询确认均已离开。

- [逐次原生、两份报告重放、用量审计](../runs/tutorial-science-matrix-002/trials/s-103/kimi-code/review/verified-001.json)。
- [全部请求、六次缺 action、末轮预算边界](../runs/tutorial-science-matrix-002/trials/s-103/kimi-code/review/completion-diagnosis-001.json)。
- [末两次输入差异与压力诊断](../runs/tutorial-science-matrix-002/trials/s-103/kimi-code/review/pressure-diagnostic-003.json)。

下面保留首报告及修改过程的细节。

首报告为 turn 000008，累计 25 次 API，引用第五次原生提交 r-000005。
12,225 单元、842 次 SIMPLE 迭代收敛。已对真实 action、输入/任务/命令绑定、
退出/日志/产物字节和原验收重放做独立核对，不是根据模型自述判断。

| 检查 | 原判定及兼容候选复核 |
|---|---|
| task_contract / 原生完成 / 场非负性 | 均通过 |
| 模型报告与产物一致 | 通过，无 mismatch |
| U、k、epsilon、nut 全场 | 全部通过 |
| p relative L2 | 0.293269，高于预设 0.15，失败 |
| p relative Linf | 0.199765，低于预设 0.5，通过 |
| 整份报告 | fail；静态兼容修复后仍 fail |

这不是 RAS 键误拒或报告格式错误。压力出口确为 fixedValue 0，不能仅因压力
未通过就擅自改成减均值比较。实际配置的 p 与 U/k/epsilon 线性求解 relTol 都为
0.1；现有证据不能单独证明误差由它造成，也没有由审阅者改算例补跑来替模型解题。
本判定代表没有达到预先固定的离散参考标准，不是对所有物理等价方案或连续真值
作普遍裁决。该首报告之后模型曾接收允许的反馈继续修改；最终状态见上文。

[真实首报告的完整只读审计](../runs/tutorial-science-matrix-002/trials/s-103/kimi-code/review/first-report-001.json)
同时保存原判定和候选判定，未覆盖生产成绩，未向模型提供私有距离或参考值。

后续 r-000006 只将 p 线性求解 tolerance 从 1e-6 收紧到 1e-7、relTol 从 0.1
收紧到 0.01；其余输入相同。压力 relative L2 为 0.293355，仍超过 0.15，其他
场仍通过。不能据此宣称收紧这两个设置就解决了问题，或直接断定最终误差来源。
[两次真实输入 diff、原生证据与压力诊断](../runs/tutorial-science-matrix-002/trials/s-103/kimi-code/review/pressure-diagnostic-001.json)
也保存模型实际收到的首报告反馈：逐项通过/失败标记及空 report_mismatch，不含
私有距离或参考值。作业 7941744、7941745 的释放凭据与独立队列查询均已核验。

此前 23:54 UTC 的过程快照中，模型已发起 51 次 API 请求（50 次结果已知），累计 7 次原生提交，
仍继续运行、无新 API 异常。第二份正式报告同样仅 field_p 失败、无报告数值失真。
第七次原生提交同时将 U 对流格式由 linearUpwind 改成 upwind，并将压力求解器由
GAMG 改成 PCG/DIC；12,225 单元，790 次迭代完成。只读产物诊断显示压力 relative
L2 为 0.375109，其他四个场仍通过。此处是产物诊断，不能冒充模型已提交了第三份
报告；两个设置一起改，也不能据此分离两者的因果影响。
[第六、七次真实输入差异及原生/全场证据](../runs/tutorial-science-matrix-002/trials/s-103/kimi-code/review/pressure-diagnostic-002.json)
保留每步退出、输入和产物哈希；相关作业 7941745、7941746 已确认离开队列。

## s-103 / Claude Code：求解及全场达标，但没有报告

终局 completed/fail，model_budget_exhausted；64 API、6 次 harness 返回，
模型耗时 1806.965 秒，原生耗时 22.867 秒。正式报告 0，不能把缺报告题改记为通过。

| 原生提交 | 实际结果 | 修正过程 |
|---|---|---|
| r-000001 | blockMesh 退出 1；controlDict.(k\|epsilon\|omega\|f\|v2) 非法文件名 | controlDict 的正则键出现额外转义引号 |
| r-000002 | 相同原生错误，退出 1 | 更改其他配置，但 controlDict 原问题仍存在 |
| r-000003 | blockMesh 退出 1；Point merge failure between face 1 of block 0 and face 0 of block 2 | 正则键改成独立字段，暴露 edgeGrading 边顺序不一致 |
| r-000004 | blockMesh、checkMesh、simpleFoam 均退出 0 | 调整两块的 edgeGrading 次序；12,225 单元，834 次迭代收敛 |

最后的全场只读诊断：

| 场 | relative L2 | relative Linf | 固定阈值 |
|---|---:|---:|---|
| U | 0.009180 | 0.032461 | 通过 |
| p | 0.028064 | 0.042599 | 通过 |
| k | 0.029398 | 0.071521 | 通过 |
| epsilon | 0.038173 | 0.147933 | 通过 |
| nut | 0.042399 | 0.089700 | 通过 |

本题同样使用原生合法的 RAS/model kEpsilon；原静态 contract 被兼容缺陷拒绝，
候选复核通过。但是**没有任何正式报告进入验收**，不能类比 Codex 的真实首报告
误拒而直接补记整题成功，也不能由审阅者代写后处理报告。

64 次 API 全部 HTTP 200、Kimi-K3 标签，无 API error、无输出截断。按实际请求
用途：主任务 25、Warmup 27、Bash 前缀分析 6、路径分析 6。最后一轮剩余 4 次，
先发生 3 次 Warmup，再发生 1 次主任务请求；实际工具仅执行
`ls -la /artifacts/r-000004/`，后续请求被已知预算拒绝。没有新的 action，因而不能
使用“最后预算轮已写 action”的恢复规则；也不是把已交好的报告弄丢。

2 次 format_failures 分别是第 4 轮没有 action，以及第 6 轮预算结束没有提交；
不是两份数值错误报告。全程 33 份工具结果中 2 个显式错误：首轮文档查询超时；
第 5 轮尝试读取已被消费的 science-action.json 时缺文件。

宿主文档统计为搜索 3、阅读 1、生成 2574 字符，但一次工具超时没有收到对应
搜索结果；此统计不能被解释为全部文档可用。该基础设施缺陷与缺报告分别报告，
不宣称单一原因解释失败，也未变更活动配额或做补偿请求。

token：input=762,401，output=30,829，cached_input=462,452，reported_reasoning=10,399，
total=793,230；无合计不一致，实际费用未知。4 个原生作业 7941734–7941737 的
释放凭据均已验证，独立队列查询确认它们已不在队列中。

- [逐运行、退出、日志、产物和用量审计](../runs/tutorial-science-matrix-002/trials/s-103/claude-code/review/verified-001.json)。
- [全部 64 次请求的用途和响应哈希](../runs/tutorial-science-matrix-002/trials/s-103/claude-code/review/request-purposes-001.json)。
- [无报告、末轮预算、全场诊断和文档错误证据](../runs/tutorial-science-matrix-002/trials/s-103/claude-code/review/completion-diagnosis-001.json)。

## s-103 / FoamClaw：工作流结束，目录/格式问题而非已测出的物理失败

已完成的前 10 次 harness 返回显示，缺 action 不能一概解释为 OpenFOAM 知识不足。
实际首个 wire 的系统提示继承原 FoamClaw：默认在 cwd 下建子目录，除非用户明确
指定绝对路径；cwd=/work。公共任务及每轮提交说明只给相对 system/science-action.json，
没有明确给出 /work/0/、/work/constant/、/work/system/。

而采集器固定调用 capture_inputs('/work')，只读取这三个根部目录，不自动寻找 /work/case。
模型实际操作与保存轨迹相符：

| 已保存返回 | 实际工具操作 | 根部捕获 |
|---|---|---|
| 000004、000005 | 写入/读取 /work/system/blockMeshDict | 1 文件，存在 |
| 000006 | 先删根部输入目录，后从已删除位置尝试复制 | 0 文件 |
| 000008 起的已审前缀 | 写 /work/case/system/blockMeshDict 和 /work/case/0/ 各场 | 0 文件 |

删除后的复制命令把 stderr 重定向，最后执行 ls，因此整体 exit=0 不证明中间 cp
成功。这里有模型脚本错误，但没有证据表明捕获器丢失了本来合规的根部文件。
另一方面，系统默认建子目录与未明确的采集根约定之间确有对接缺口；该协议问题
应与模型物理错误分列，不可用这些空捕获轮数单独排名 CFD 能力。

[原始前缀证据](../runs/tutorial-science-matrix-002/trials/s-103/foamclaw/review/workspace-layout-001.json)
包含实际请求哈希、legacy 系统提示来源、工具事件与逐轮捕获。它不是终局判定，
不覆盖之后所有动作，也不证明一个更清楚的提示就一定能完成物理题。

现有假 API 接口测试直接写入正确的绝对路径，没有检查真实 FoamClaw 默认提示
是否与目录协议对齐。[最小后续修正及应补测试](../review_candidates/workspace_contract_v1/README.md)
已记录：统一向四个 harness 明确绝对 case/action 路径，缺 action 时返回准确公共
路径反馈。已完成隔离候选、49 项假执行器测试以及四个真实客户端的本地假 API
两轮提交/恢复测试。完整回归及版本化部署仍待完成；未修改活动提示、采集器
或成绩，也未付费重试。

另一个影响必须与新目录问题区分：本实验预先冻结的 FoamClaw controlled 配置为
max_history=50、observation_only、无 persistent_memory。已核对
submission-18/api/call-004 的真实 wire：51 条消息（系统提示 + 最近 50 条），
首个完整用户任务不再存在，题目标题与必需的 epsilon_cell_min_mean_max 指标名
也不再存在；每轮相对 action 路径提醒仍存在。
[两份实际 wire 的对照凭据](../runs/tutorial-science-matrix-002/trials/s-103/foamclaw/review/history-window-001.json)
证明此时上下文发生裁剪，不证明模型内部“忘了什么”或已有文件不含相关数据。
这是冻结的 harness 记忆配置行为，不是新发生的 API 报错，也不是此次临时增加的
token 上限。当前结果测的是受控工具下整套 harness 的任务完成能力，不能只归因于
Kimi-K3 的物理知识；没有在本题中途改大记忆或重新发送原题。

### 本题最终定量记录

原始结论 completed/fail，model_budget_exhausted；64 次 API、25 次 harness 返回，
原生提交 0、正式报告验收 0、模型耗时 1597.244 秒、原生耗时 0。
25 次格式反馈拆分如下，不能一概叫“空输出”：

| 类型 | 次数 | 原文 |
|---|---:|---|
| 根部没有新 action | 17 | Expecting value: line 1 column 1 (char 0) |
| 根部已有 JSON，但不符合动作 schema | 8 | Expected exact task run or report action |

后八次捕获说明模型最终尝试写根部 action，但没有按公开格式提交。一个实际例子：

```json
{"action":"run","commands":["cd /work/case && blockMesh","cd /work/case && simpleFoam"]}
```

本题公开要求为 `{"action":"run","solver":"simpleFoam"}`。另有 type / task /
command 等字段变体。已审后续请求中，完整原题不再出现；现有证据同时涉及目录
歧义、历史裁剪和动作字段错误，不能断言只有某一个原因，更不能当成物理验收失败。
最后一个 action 已由旧版预算边界修复正确捕获（accepted_terminal_action=true），
随后正常进入 schema 检查；不是“最后轮写好了却被适配器忽略”的旧 bug。

64 次请求都有 HTTP 200 和完整响应，model 标签均为 Kimi-K3，没有 API error 凭据。
最长一次 submission-18/call-004 用时 292.384 秒后正常返回，不是超时或 429。
无法仅凭总耗时区分上游排队和模型生成时间。

工具级记录有两次非零退出：一次尝试不存在的 shell 命令 apply_patch，导致 action
未写入；另一次包含多项 find/env/grep，最终 grep 无匹配退出 1。这些都不是求解器错误。
文档搜索 1 次、阅读 0 次，返回 1266 字符。
input=583,378、output=25,658、cached_input=209,973、reported_reasoning=8,184；
供应商 total=609,029，比 input+output 少 7（submission-21/call-002），费用未知。

- [原始终局轨迹审计](../runs/tutorial-science-matrix-002/trials/s-103/foamclaw/review/verified-001.json)。
- [25 次格式错误、8 份实际 action 和 64 次 API 的逐项证据](../runs/tutorial-science-matrix-002/trials/s-103/foamclaw/review/format-diagnosis-001.json)。

由于没有有效原生提交，不补跑模型未提交的 /work/case，也不猜它的物理正确性。
独立控制器已自动进入 s-103 / Claude Code；原始分母保留，目录协议影响待正式修复后审阅。

## s-103 / Codex：首报告被 RAS 字段兼容性缺陷误拒

已验证的首份正式报告是 turn 000009，引用 r-000002；累计 33 次 API 调用，
9 次 harness 返回、6 次缺 action 格式反馈、2 次原生提交。其中首次原生提交缺少
system/blockMeshDict，在 blockMesh 阶段失败；第二次全部命令正常退出。

原生 r-000002 的 blockMesh、checkMesh、simpleFoam 退出均为 0，累计 14.358 秒。
12,225 个单元，SIMPLE 在 786 次迭代收敛；日志明确输出：

```text
Selecting turbulence model type RAS
Selecting RAS turbulence model kEpsilon
SIMPLE solution converged in 786 iterations
```

| 独立验收项 | 原判定 | 候选修复后 |
|---|---|---|
| 原生完成 / 场非负性 | 通过 / 通过 | 不变 |
| U relative L2 / Linf | 0.012623 / 0.065620，通过 | 不变 |
| epsilon relative L2 / Linf | 0.097661 / 0.140024，通过 | 不变 |
| k relative L2 / Linf | 0.063871 / 0.093599，通过 | 不变 |
| nut relative L2 / Linf | 0.050941 / 0.108055，通过 | 不变 |
| p relative L2 / Linf | 0.097828 / 0.089094，通过 | 不变 |
| 模型报告与实际产物一致 | 通过，0 差异 | 不变 |
| 静态 task_contract | unreadable_material_or_turbulence_model | 通过 |
| 整份真实报告 | fail | **候选复核 pass** |

模型的实际配置是 `RAS { model kEpsilon; turbulence on; printCoeffs on; }`。
v2306 原始 RASModel.C 使用 `getCompat<word>("model", {{"RASModel", -2006}})`，
model 为首选，RASModel 才是旧键；我们的检查器却只读取后者。这是验收器错误，
不是物理模型错误或中转 API 错误。候选同时按原生源码支持省略 turbulence 时默认 on，
但仍拒绝关闭、错误模型、自定义未登记系数；数值误差阈值没有放宽。

首报告之前只收到 6 次确有缺 action 的格式反馈及 2 次真实原生运行反馈，没有报告
评分反馈。只读审计复核了输入/任务/命令绑定、退出、日志、产物实际字节、原始评分
重放及资源释放。**第 33 次调用的这份正确提交真实存在，不是审阅者代写报告**。
之后的额外调用和重跑是错误负反馈下的续作，不能用来宣称模型必须花这么多调用
才能解出本题；当前未覆盖原始成绩，也未付费重发。

首报告前的 33 次 API 均逐一找到 dispatch、wire_request、HTTP 200、response.raw
和 complete 凭据；请求与响应标签均为 Kimi-K3，未出现 error 凭据，也未设置请求
级 max_tokens/max_output_tokens/max_completion_tokens 字段。这仅证明可见链路标签，
不是对中转站实际权重的独立认证。

错误反馈后 r-000002 → r-000003 的实际改动：删除冗余 constant/momentumTransport；
controlDict 删除空 functions 和显式 writeCompression off；fvSolution 删除 consistent yes
和 cache/grad(U)，调整 residualControl 的正则覆盖及松弛项排布。真实湍流键 model
未改，后一次仍完成且各项定量比较与报告一致性通过，因此 turn 000012 又被同一
静态字段缺陷误拒。不能把这些在误导反馈后的尝试算成独立采样或无干扰的调用效率。

- [真实首报告及原始判定](../runs/tutorial-science-matrix-002/trials/s-103/codex/run/evaluations/000009/result.json)。
- [首报告完整兼容修正审计](../runs/tutorial-science-matrix-002/trials/s-103/codex/review/v2306-first-report-001.json)。
- [首报告前 33 次 API 凭据审计](../runs/tutorial-science-matrix-002/trials/s-103/codex/review/first-report-api-prefix-001.json)。
- [全体现有报告的最新影响快照](../runs/tutorial-science-matrix-002/review/v2306-compat-impact-004.json)（保留先前 001–003 快照）。
- [隔离修复候选、114 项测试及重放方法](../review_candidates/v2306_compat_v1/README.md)。

这些是既有证据的独立候选复核，不是已经部署的新版本成绩。活动流程结束后仍需
正式全套回归、版本化验收与明确标注的修正汇总；不能把当前原始流程当成干净排名。

### 原始流程终止记录与费用归因

s-103 / Codex 最终在 64 次 API 后按原规则结束：completed/fail，
model_budget_exhausted。共 18 次 harness 返回、4 次原生提交、11 次缺 action、
3 次正式报告误拒；原生启动失败 1 次、数值运行失败 0 次。
第三份报告 turn 000018 也所有数值/报告检查通过，只被同一 RAS 键错误拒绝。
r-000004 与 r-000003 输入完全相同，是错误反馈之后的重复运行。

| 统计 | 原始全轨迹 | 首份合格报告前 |
|---|---:|---:|
| API 调用 | 64 | 33 |
| harness 返回 | 18 | 9 |
| 原生提交 | 4 | 2 |
| 模型耗时统计 | 2332.537 s | 951.358 s |
| 原生耗时 | 43.659 s | 14.678 s |

多出的 31 次请求属于误拒后的续作，不能用于估计无此验收 bug 时的解题效率。
一个真实后处理脚本错误发生在 turn 000008：错误识别 OpenFOAM internalField，
读出 cell_count=0，随后 ZeroDivisionError；模型下一次返回修复并交出合格报告。
这 1 次模型脚本错误与 3 次验收器误拒分开统计。

原始用量：input=2,493,149、output=27,177、cached_input=1,784,449，
reported_reasoning=2,407；供应商 total=2,520,319，比 input+output 少 7。
差异来自 submission-01/call-007；保留原值，不据此改变答案分数。费用未知，
上游未报告可识别金额。文档搜索 7 次、阅读 4 次，共返回 18,504 字符。

[四次原生与三份正式报告的原始重放审计](../runs/tutorial-science-matrix-002/trials/s-103/codex/review/verified-001.json)
验证原始记录可重现，但不表示原规则正确。独立控制器随后自动进入 s-103 / FoamClaw，
没有手动补发或重新启动批次。

## 启动证据

- 批次：[tutorial-science-matrix-002](../runs/tutorial-science-matrix-002/)。
- [用户付费授权凭据](../runs/tutorial-science-matrix-002/private/paid-authorization.json)。
- [536 项完整回归](../runs/tutorial-science-matrix-002/private/tests.json)。
- [五题各六项原生资格](../runs/tutorial-science-qualification-002/report.md)。
- 控制器 PID / session ID：2149511 / 2149511；启动时钟 4185522177。
- [独立控制器凭据](../runs/tutorial-science-matrix-002/controller/1d765ea1b5c04f3b9c261357c0ecb7e7/)。
- 启动命令退出后再次核对：控制器仍存活，无退出凭据，已进入 s-101 / Codex。

任务调度、原生执行和实时表更新由独立控制器负责，不需要主 agent 再发送“继续”。
不要对活动批次重复 launch；不要因观察超时或请求未返回就重新付费发送。
旧 001 的 217 次调用和原始成绩保留，不合并成 002 的分数。
旧版缺陷和受影响轨迹见[修复说明](VERIFIER_BOUNDARY_FIX.md)。

## 直接看进度和过程

- [实时总表](../runs/tutorial-science-matrix-002/scoreboard.md)：20 个试验完整分母。
- [控制器日志](../runs/tutorial-science-matrix-002/controller.log)：阶段变化、结束和异常。
- [首题真实客户端轨迹](../runs/tutorial-science-matrix-002/trials/s-101/codex/agent/)。
- 各题输入和报告：trials/任务/harness/run/turns/。
- 独立原生证据：对应 native/runs/；定量验收：run/evaluations/。

控制器每 5 秒读取状态，日志仅在变化时输出；统计表只读记录，不启动补算。
尚未完成的试验不填成答案失败，基础设施问题单列；完成整批之前不报最终排名。
模型说“我提交了”不算证据，实际 action、退出码、原生产物和独立检查才计入结果。

## 首次 API 链路核对

首题 s-101 / Codex 的首 5 次请求均收到 HTTP 200，实际请求 model 与响应 model
均标为 Kimi-K3，finish_reason 为 tool_calls，返回的 exec_command 已交给真实客户端处理。
对应耗时约为 10.00、10.14、26.01、8.41、6.11 秒；没有记录限流或其他 API 异常。
这是已观测请求的情况，不是全批次无故障保证，也不是对上游模型权重身份的独立认证。

开始时没有任何已完成的试验。后续变化以实时总表为准；具体失败、实际修改和
验收差异将在本文件单独记录，不只给一个 pass/fail，也不将私有参考误差送回模型。

## s-101 / Codex：最终通过；以下保留过程

第一个 harness 返回共使用 7 次模型调用，提交一次正式运行，未出现提交格式失败。
r-000001 的 blockMesh、checkMesh、icoFoam 都有完整退出凭据，退出码分别为 0、0、0；
原生累计执行约 2.851 秒。此时尚未独立验收，不能把原生通过当作整题通过。
控制器已自动恢复同一客户端会话读取输出和后处理，不需要人工推动下一步。

两次客户端启动凭据均包含 --unshare-all，submission_protocol 均为
fresh-action-v2-budget-boundary；没有混用旧提交协议。

[首次运行证据](../runs/tutorial-science-matrix-002/trials/s-101/codex/native/runs/r-000001/)、
[本题实时表](../runs/tutorial-science-matrix-002/trials/s-101/codex/run/scoreboard.md)。

第二次 harness 返回使用 2 次调用，客户端正常结束，但没有写出新 action，记一次
提交格式失败。原始响应将“曾调用工具 exec_command”和拟执行脚本写在普通文本中，
并非已执行的正式工具调用；控制器已按正常反馈继续同一会话。不能把文字中的
脚本当成已经运行，更不能声称报告已提交。此处与旧版“有效末轮 action 被忽略”
不同：该次保存文件中确实没有 action，且尚未耗尽模型预算。

第三次返回又使用 6 次调用，真实执行了后处理并提交最终报告。最初一次脚本错误：

```text
init, final = res[-1]
IndexError: list index out of range
```

模型用 `log.rfind('Time = ')` 截取最后时间块，却命中了日志末尾 `ClockTime = 0 s`
的子串，因此没有找到压力残差。模型查看日志、打印实际截取结果后，改用行首匹配
`(?m)^Time = `，重新计算并写出真正的 action。这个错误发生在模型自写脚本中，
不是验收器解析错误；本次真实后处理脚本失败 1 次，与缺 action 的 1 次格式失败分列。

| 指标 | 核验结果 |
|---|---|
| 最终判定 | pass，所有独立检查通过 |
| API / harness 返回 / 原生运行 | 15 / 3 / 1 |
| 原生启动失败 / 数值运行失败 | 0 / 0 |
| 提交格式失败 / 后处理脚本失败 / 报告验收失败 | 1 / 1 / 0 |
| 最终时间 / 单元数 | 0.5 s / 400 |
| U relative L2 / Linf | 1.048484519e-6 / 5.849880434e-7 |
| p relative L2 / Linf | 1.338755562e-6 / 1.034919891e-6 |
| 模型耗时统计 / 原生执行时间 | 268.909 s / 2.851 s |
| 文档访问 | 搜索 1 次、阅读 0 次，返回 2890 字符 |
| 输入 / 输出 token | 288316 / 6865；缓存输入 92268，已报告推理 174 |
| 费用 | 未知，上游未报告可识别金额和币种 |

注意：上游有一条用量不自洽。submission-01/call-005 原文 prompt=11580、
completion=99、total=11672，比前两者之和少 7；所以原样汇总 total=295174，
而 input+output=295181。不擅自改写凭据，也不把这一用量问题当成答案失败。

只读审计已复核：原生 task/input/命令绑定、各步退出和日志、产物哈希、模型可见
只读产物的实际字节、资源释放凭据。重新计算完整验收对象，与原保存结果完全一致。
作业 7941400 已独立查询确认不在活动队列。没有调用模型或重跑 OpenFOAM。

[最终独立验收](../runs/tutorial-science-matrix-002/trials/s-101/codex/run/evaluations/000003/result.json)、
[三次提交快照](../runs/tutorial-science-matrix-002/trials/s-101/codex/run/turns/)。

## s-101 / FoamClaw：最终通过；目录与提交问题显著增加调用

最初将完整算例写在 `/work/lidDrivenCavity/`，而任务服务从 `/work` 根目录读取
0/、constant/、system/。因此首轮保存的受评输入集合为空，未正式提交 OpenFOAM。
后续模型文本已识别预期 action 位于 `/work/system/science-action.json`，但出现多次
“接下来会写/检查”的正常结束文本而未真正创建根目录输入及 action。

模型第八次返回时自行搬回根目录并写出了正确运行 action；前七次为缺提交的格式
反馈。第九、十次返回发生在原生运行成功之后，又没有写出新报告 action；第十一次
真实执行后处理并交出报告。合计 9 次格式失败应拆成运行前 7 次、运行后 2 次，
不是 9 次 OpenFOAM 启动失败，也不是运行前一直没有根目录文件。

没有由审阅者搬文件或代写报告。唯一实际非零工具退出是第三轮检查不存在的
`/work/system/` 时 `ls` 返回 2；不是后处理脚本失败。第十一轮两次实际后处理脚本
均退出 0。模型查看过自己的 `/opt/worker/foam_worker.py`，这是可见 harness 包装器，
不是隐藏验收器、参考或密钥；不能把这次读取称作拿到了参考答案。

| 指标 | 核验结果 |
|---|---|
| 最终判定 | pass，所有 6 项独立检查通过 |
| API / harness 返回 / 原生运行 | 29 / 11 / 1 |
| 原生启动失败 / 数值运行失败 | 0 / 0 |
| 提交格式失败 / 后处理脚本失败 / 报告验收失败 | 9 / 0 / 0 |
| 其他非零工具退出 | 1，查询尚不存在的目录 |
| 最终时间 / 单元数 | 0.5 s / 400 |
| U relative L2 / Linf | 1.048486330e-6 / 5.850009441e-7 |
| p relative L2 / Linf | 1.338778706e-6 / 1.034997859e-6 |
| 模型耗时统计 / 原生执行时间 | 312.003 s / 0.706 s |
| 文档访问 | 0 次，无查询凭据 |
| 输入 / 输出 token | 319478 / 7735；缓存输入 186265，已报告推理 0 |
| 费用 | 未知，上游未报告可识别金额和币种 |

原始上游用量同样有一条少 7：submission-01/call-002 的 prompt=3594、completion=37、
total=3624。因此原样总计 327206，而 input+output=327213。没有据此推断实际计费。

已只读复核 task/input/命令/包装器绑定、三个退出码（均为 0）、日志、全部 5 个
产物的哈希和模型可见字节、物理约束以及完整验收对象；复算结果与保存结果完全
一致。作业 7941402 有释放凭据，且独立集群查询确认已不在活动队列。

[最终独立验收](../runs/tutorial-science-matrix-002/trials/s-101/foamclaw/run/evaluations/000011/result.json)、
[十一轮快照](../runs/tutorial-science-matrix-002/trials/s-101/foamclaw/run/turns/)、
[原生证据](../runs/tutorial-science-matrix-002/trials/s-101/foamclaw/native/runs/r-000001/)。

目前两条已审计的结果说明这道层流腔体题能被两种 harness 完成，但不足以推断
五题整批通过率，更不能仅凭格式迭代次数断言模型物理知识不足。

## s-101 / Claude Code：最终通过；真实后处理脚本失败 3 次

第一个 harness 返回使用 11 次 API 调用，提交的原生运行已经完成，没有启动或
数值失败。第二轮使用 30 次 API 调用，后处理轨迹如下：

- 检查不存在的 `/artifacts/r-000001/log`（实际为 solver.log 等）使一次目录查询
  返回 2；这不是原生产物缺失。
- 自写 postprocess.py 用非贪婪括号正则读取向量列表，先在第一个向量的右括号
  截断，实际读到 1 个向量，断言报 `AssertionError: (1, 400)`。
- 第一次修正只改了内部向量匹配，没有修复外层截断，变成
  `AssertionError: (0, 400)`。模型随后检查实际字节并继续修改。
- 第二次修正了外层匹配，但 `map(float, t)` 把整个字符串按字符转换，第三次
  报 `ValueError: could not convert string to float: '.'`。
- 最后限定到 internalField 列表的结束位置，并使用 `t.split()` 拆开 xyz，
  成功读取 400 个向量，执行脚本并把输出写到真正的报告 action。

三次退出 1 都来自真实执行的模型自写脚本，不是验收器读取速度场时报错。
同一后处理脚本也有两次成功执行：先查看输出，再重定向成报告。

| 指标 | 核验结果 |
|---|---|
| 最终判定 | pass，所有 6 项独立检查通过 |
| API / harness 返回 / 原生运行 | 41 / 2 / 1 |
| 原生启动失败 / 数值运行失败 | 0 / 0 |
| 提交格式失败 / 后处理脚本失败 / 报告验收失败 | 0 / 3 / 0 |
| 其他非零工具退出 | 1，查询不存在的 log 路径 |
| 最终时间 / 单元数 | 0.5 s / 400 |
| U relative L2 / Linf | 4.107289315e-6 / 2.306988543e-6 |
| p relative L2 / Linf | 2.373801367e-6 / 1.261691518e-6 |
| 模型耗时统计 / 原生执行时间 | 665.152 s / 0.702 s |
| 文档访问 | 0 次，无查询凭据 |
| 输入 / 输出 token | 416860 / 11555；缓存输入 279010，已报告推理 6176 |
| 费用 | 未知，上游未报告可识别金额和币种 |

41 条 API 均有终态响应，未记录 API 异常；包括客户端辅助调用，不是 41 次
算例提交。本题未发现上游 input+output 与 total 的不一致。输出、缓存、推理数字
按上游字段原样汇总，不把缓存或推理 token 再累加一遍。

已只读复核 task/input/命令/包装器绑定、三步原生退出和日志、产物哈希及可见
字节、物理约束以及完整验收对象，结果完全一致。作业 7941693 有释放凭据，
独立集群查询确认不在活动队列。没有重新调用模型或运行 OpenFOAM。

[原始 Claude Code 轨迹](../runs/tutorial-science-matrix-002/trials/s-101/claude-code/agent/)、
[最终验收](../runs/tutorial-science-matrix-002/trials/s-101/claude-code/run/evaluations/000002/result.json)、
[只读审计凭据](../runs/tutorial-science-matrix-002/trials/s-101/claude-code/review/verified-002.json)。

审阅文件说明：Claude Code 的第一份 review/verified-001.json 在审阅工具复制时
经过 JavaScript JSON 重新编码，将原本 Python 浮点 `0.0` 表示成整数 `0`，导致
该副本自身的内容哈希校验失败。这个副本保留但作废；没有修改正式 run/results、
run/evaluations 或原始轨迹。随后重新进行只读审计，逐字保存 Python 输出为
verified-002.json 并重新读取验哈希成功。它是审阅材料复制问题，不是模型提交
失败，也不影响原始评分；后续审计凭据禁止跨语言解析再重编码。

## s-101 / Kimi Code：最终通过；普通文本工具描述导致多轮漏交

首轮 5 次调用后已真正保存输入和运行 action，第一次 OpenFOAM 运行成功。
第 2–7 次 harness 返回都没有新 action，合计 6 次格式失败，全部在运行之后。
原始响应多次把拟执行操作写成普通文字，例如 `[曾调用工具 Write]` 或
`[曾调用工具 Bash]`，但 `tool_calls` 为空；客户端没有把文字当代码执行。
模型因此误以为已经写出 postprocess.py，后来检查才发现该文件不存在。

第 8 次返回真实执行了内联后处理脚本，第一次将残差末尾逗号也传给 float：

```text
ValueError: could not convert string to float: '5.56292517185e-07,'
```

模型自行修正数字提取后写出报告并检查 JSON；最终所有报告数字和全场验收通过。
另有一次试图调用未提供的 `cnb_pipeline_syntax`，客户端返回
`Tool "cnb_pipeline_syntax" not found`。不能把这算作 OpenFOAM 或 HTTP 错误。

| 指标 | 核验结果 |
|---|---|
| 最终判定 | pass，所有 6 项独立检查通过 |
| API / harness 返回 / 原生运行 | 18 / 8 / 1 |
| 原生启动失败 / 数值运行失败 | 0 / 0 |
| 提交格式失败 / 报告验收失败 | 6 / 0 |
| 后处理启动失败 / 脚本内异常 | 1（文件不存在）/ 1（残差含逗号） |
| 未提供工具调用 | 1（cnb_pipeline_syntax） |
| 最终时间 / 单元数 | 0.5 s / 400 |
| U relative L2 / Linf | 1.083303613e-6 / 6.575931753e-7 |
| p relative L2 / Linf | 1.339078589e-6 / 1.036210152e-6 |
| 模型耗时统计 / 原生执行时间 | 236.120 s / 0.699 s |
| 文档访问 | 搜索 1 次、阅读 0 次，返回 2466 字符 |
| 输入 / 输出 token | 456079 / 8459；缓存输入 42151，已报告推理 0 |
| 费用 | 未知，上游未报告可识别金额和币种 |

Kimi Code 的 12 条工具结果是文本记录，未包含独立结构化退出码；上述两项
后处理失败来自明确的错误文本，而不是捏造退出码。命令还使用了 `| tail`，
所以不能假设 shell 整体退出码等于前面的 Python 退出码。原生运行的三个
退出码则均有独立凭据，均为 0。

上游用量有两条分别少 7：submission-05/call-001 的 39892+50 对应 total=39935；
submission-06/call-001 的 41747+42 对应 total=41782。原样 total 合计 464524，
而 input+output=464538。未将这项计数不一致作为答案失败。

已只读核验 task/input/命令/包装器、原生退出/日志/全部产物、实际可见字节和
完整定量验收，重算对象与原始结果完全一致。作业 7941697 已释放，独立查询
确认不在活动队列。

[完整验收及工具观察凭据](../runs/tutorial-science-matrix-002/trials/s-101/kimi-code/review/verified-001.json)、
[最终报告验收](../runs/tutorial-science-matrix-002/trials/s-101/kimi-code/run/evaluations/000008/result.json)、
[客户端轨迹](../runs/tutorial-science-matrix-002/trials/s-101/kimi-code/agent/)。

### 上游文本工具标记的归因边界

首次出现位置是 Kimi Code submission-01/api/call-005/response.raw：
原始响应已经包含 `[曾调用工具 Write]`，finish_reason=stop，结构化 tool_calls=0。
该请求的 request.json 与真正发送的 wire_request.json 中都没有该标记，之前
四次请求也没有。请求提供了正常的 Write/Bash 等工具定义。

broker.py 在 HTTP 返回后先逐字保存 response.raw，之后才调用协议转换；
已检查的项目协议/适配代码中未发现这个文字标记。这排除了本次“有效工具调用
被适配器转成该段文字后丢失”的解释。它首先在上游原始响应中出现，但仅凭客户端
证据不能进一步区分模型生成、上游模型模板或中转平台处理，不能宣称已证明是哪一方。

这些记录说明此轮测到的是固定模型 API 链路下的 harness 组合表现。提交格式、
工具调用和后处理成本都值得记录，但不能全部解释成 OpenFOAM 物理知识差距。

## s-101 小结（仅首题，不是整批排名）

| Harness | 定量验收 | API 调用 | 漏交新 action | 后处理启动失败 | 脚本内异常 | 原生运行 |
|---|---|---:|---:|---:|---:|---:|
| Codex | pass | 15 | 1 | 0 | 1 | 1 |
| FoamClaw | pass | 29 | 9 | 0 | 0 | 1 |
| Claude Code | pass | 41 | 0 | 0 | 3 | 1 |
| Kimi Code | pass | 18 | 6 | 1 | 1 | 1 |

四条均完成 400 单元、0.5 秒任务；没有原生启动、数值运行或最终报告验收失败。
API 数包含真实客户端辅助请求，故不等于推理主循环轮数。首题结束时已完成 4/20，
后续 s-102–s-105 仍须按冻结配置完成，不能由这道较简单的腔体题外推整批表现。

### 首题 API 身份与客户端输出设置核验

逐条检查了四个 harness 合计 103 次真实 wire_request、response.raw 和 HTTP 凭据：
请求 model 和响应 model 全部标为 Kimi-K3，103 条 HTTP 状态均为 200。
这证明记录中的路由标识一致，不等于独立验证上游实际模型权重。HTTP 200 也
不代表工具调用或最终答案一定正确，上述普通文本工具描述就是反例。

| Harness | 实际 wire 输出 token 字段 | 请求数 |
|---|---|---:|
| Codex | 未设置 max_tokens / max_completion_tokens | 15 |
| FoamClaw | 未设置 max_tokens / max_completion_tokens | 29 |
| Claude Code | 客户端 max_tokens=32000 | 41 |
| Kimi Code | 客户端动态 max_tokens=112539–131072 | 18 |

上述 max_tokens 是客户端自身携带并由桥接保留，不是评测器新加的单次预算。
因此准确说法是“评测层不强行加单次上限”，不是“所有客户端发出的请求都没有
输出长度设置”。首题未记录输出截断；费用未报告的仍记未知，不自行套用价格。

### 首题实际隔离启动凭据复核

复核了 Codex 3、FoamClaw 11、Claude Code 2、Kimi Code 8 次，共 24 次实际
launch.json：均含 `--unshare-all`、`--clearenv`、`--chdir /work`。/work 与
/home/agent 均绑定到当前试验专属目录，/artifacts 只读绑定到当前试验的
run/artifacts；文档客户端、API socket 和桥接脚本为只读绑定。没有参考、验收器、
其他试验成绩或宿主凭据目录的挂载。额外只读路径仅为对应客户端运行材料。

这是实际启动参数的检查，与此前真实客户端隔离回归测试相互补充，不以参数
本身冒充所有运行时安全性质的完整证明。后续题的启动凭据仍须逐批检查。

## s-102 / Codex：基础设施中断，不是模型物理失败

前三次 harness 返回合计 11 次 API 调用，分别保存 1、3、3 个输入文件，均未
写出运行 action，记录 3 次格式失败。多次原始响应含普通文本工具描述，不能
把描述中的脚本当作已执行。

第四次返回的第一笔请求（本题累计第 12 笔）在预先设置的 600 秒网络等待后
触发异常。原始 error.json 为：

```json
{"call": 1, "known_response": false, "reason": "ReadTimeout", "type": "ReadTimeout"}
```

该请求有 dispatch 凭据，但没有 HTTP 状态、complete 或 response.raw；这是
未收到响应的读取超时，不是观察到 429、500 或 OpenFOAM 报错。仅凭此证据
不能区分上游排队、生成缓慢、网络问题或平台故障，也不知道上游是否已完成/计费。

客户端子进程退出码 1，持续 601.592 秒；其 exit.json 中 timed_out=false 指外层
进程看门狗没有强行杀进程，**不表示 API 没超时**。API 超时由上述 ReadTimeout
凭据记录。已独立查验子进程 2233876 消失，控制器 2149511 仍存活。

| 指标 | 结果 |
|---|---|
| 生命周期 / 运维结论 | interrupted / error |
| 原因 | model_request_outcome_unresolved |
| 已发 API / 已知 HTTP 响应 | 12 / 11 |
| 正式原生提交 / 私有验收 | 0 / 0 |
| 模型物理对错 | 未测得，不能记 fail 或 pass |
| 费用 | 未知，不能因没返回就记为未计费 |

原请求没有重发，12 次调用未被清零；本项仍保留在 20 条注册清单中，并在
基础设施异常列单列。控制器已自动进入 s-102 / FoamClaw；不会因为一项超时
就停止其他已授权试验。若以后要补测，须建立独立新尝试、保留这条中断记录，
不能覆盖成一次无异常的首次作答，也不能假定重新请求不产生额外费用。

[中断审计凭据](../runs/tutorial-science-matrix-002/trials/s-102/codex/review/interrupted-001.json)、
[原始失败请求](../runs/tutorial-science-matrix-002/trials/s-102/codex/agent/57117abbf2ca4e2fb08282f649cf22e6/submission-04/api/call-001/)、
[本项实时表](../runs/tutorial-science-matrix-002/trials/s-102/codex/run/scoreboard.md)。

## s-102 / FoamClaw：最终失败；以下先保留两次运行的过程

累计 15 次 API 调用、5 次漏交 action 后，提交 r-000001。blockMesh、checkMesh
均退出 0，simpleFoam 在第 1 次 SIMPLE 迭代的速度方程之后中止，退出码 -6：

```text
Creating lduPrimitiveAssembly: lduAssembly01
FOAM FATAL ERROR: (openfoam-2306)
Attempt to cast type lduPrimitiveMeshAssembly to type fvMesh
```

本次提交的 system/fvSolution 给压力选择了 `solver GAMG`、
`agglomerator faceAreaPair`，栈回溯指向 `faceAreaPairGAMGAgglomeration` 的构造和
fvMesh 强制转换。这是该提交在当前隐式 AMI 组装路径下的原生配置兼容错误；
不是 HTTP 故障，不是独立验收器解析错误，也不能推广成所有 GAMG/AMI 组合均不支持。

本次累计原生执行 3.344 秒。计数器阶段为 numerical，是因为日志已经出现
`Solving for Ux/Uy`；该标签只表示“开始求解之后失败”，此例不是已证明的数值发散。

另一个独立问题：提交新增了 SIMPLE/residualControl（p=1e-5、U=1e-6），而题面
规定固定 100 次迭代、不提前收敛。因此私有公共约束复核记录
`unregistered_early_convergence`。这不是上述原生崩溃的原因，不能混为一谈。

控制器已把本次清理过的原生日志返回同一会话继续修改；尚未产生最终物理成绩。
没有向模型追加私有参考数值或人工修复提示，后续以其真实新提交为准。

[首次原生运行及输入](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/native/runs/r-000001/)、
[本项过程表](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/run/scoreboard.md)。

后续实际文件变化（run/turns/000010 快照，不是模型文字承诺）：压力求解器已由
GAMG 改为 PCG，并新增 preconditioner DIC；删除了 GAMG 的 smoother、agglomerator、
nPreSweeps、nPostSweeps、cacheAgglomeration、nCellsInCoarsestLevel、mergeLevels。
fvSchemes 未改变，SIMPLE/residualControl 仍在。这个快照没有新的 science-action.json，
所以只能确认修改已落盘，不能声称修改后的配置已由 OpenFOAM 验证。

首次失败原生运行已另做只读审计：task/input/命令/包装器绑定、三步退出、日志、
产物字节、失败分类、公共约束复核全部与保存结果一致。作业 7941701 的释放凭据
存在，独立集群查询也确认不在活动队列。此时未产生最终报告，审计中的
evaluations_replayed=0、evaluation_replay_exact_match=null，不把缺少验收记录当通过。
见[首次运行审计](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/review/native-000001-audit.json)。

### 第二次运行与正式终态

r-000002 使用已修改的 PCG + DIC，三个原生命令均退出 0，实际完成 100 次
SIMPLE 迭代，共 0.918 秒。残留的 residualControl 没有触发提前结束；静态公共
配置检查仍记录 `unregistered_early_convergence`，两者必须区分。本项并没有
因为这条静态检查直接得出最终失败：最终没有任何合法报告进入正式验收。

| 指标 | 最终记录 |
|---|---|
| 正式结论 / 原因 | fail / model_budget_exhausted |
| API / harness 返回 | 64 / 37 |
| 原生提交 / 完整运行成功 | 2 / 1 |
| 原生启动失败 / 开始求解后失败 | 0 / 1（GAMG 组装兼容错误） |
| 格式失败 | 35：32 次缺新 action，3 次 JSON 结构不符合报告协议 |
| 正式报告验收次数 / 验收失败次数 | 0 / 0；不是说所有报告正确，而是没有合格入口 |
| 模型耗时统计 / 原生命令执行累计 | 1246.635 s / 4.262 s |
| 文档查询 | 0 次 |
| 输入 / 输出 token | 1140618 / 11846；缓存输入 184478，已报告推理 0 |
| 费用 | 未知 |

64 条请求都有 HTTP 200 和终态响应，没有 API 异常或输出截断。一次正常返回
花了约 302 秒，不应与 Codex 的 ReadTimeout 混为一谈。用量有两条 total 各少 7：
submission-26/call-001 的 16061+25 对应 16079；submission-34/call-001 的
35411+391 对应 35795。原样 total=1152450，而 input+output=1152464。

三份 JSON 的问题不是 JSON 语法无法解析，而是提交内容、字段和单位协议不符：

| 快照 | 实际顶层字段 | 主要缺失/不符 |
|---|---|---|
| 000014 | action/status/run_id/case/solver/mesh/numerical/results | 缺 measurements；自选左右区域统计，没有要求的完整带单位指标 |
| 000028 | action/solver/results | 缺 run_id 和 measurements；仍为自选区域统计 |
| 000034 | action/run_id/solver/status/metrics | 使用 metrics 而非 measurements，且未按指定量和单位提交 |

协议要求顶层严格为 action、run_id、measurements，measurements 内为题面列出的
全场统计和单位对象。不能把这些不同物理量的自选统计自动映射成所需报告。
实际快照见 [000014](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/run/turns/000014/result.json)、
[000028](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/run/turns/000028/result.json)、
[000034](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/run/turns/000034/result.json)。

### 已证实的上下文管理问题

原 FoamClaw 的 ConversationMemory.add 在超过 50 条消息时直接保留最后 50 条，
不固定保存原始用户任务。桥接沿用这个已冻结的原配置；首次发送题面，以后通过
原客户端会话只发送新反馈。checkpoint 也仅保存当前已截断消息，而不是完整档案。

首笔 wire 请求含题面开头与 “Write your own postprocessor” 说明；后期
submission-31/call-003、submission-32/33/34 的实际 wire 请求均为 51 条消息
（系统消息加最近 50 条），这些原始说明已不在其中。最终 foam-session.json
同样只有 50 条消息，未保留这两处说明。轨迹中模型开始反复表示需要到 session
文件中寻找报告格式。这是直接观察到的上下文丢失，不是以最终失败倒推记忆问题。

相关源码：[ConversationMemory.add](../../foamclaw/core/memory.py)、
[原 worker 的记忆与 checkpoint](../agentcfd_bench/smoke/foam_worker.py)、
[首次题面/后续反馈](../agentcfd_bench/smoke/agent.py)。这是本次被测 FoamClaw
组合的实际弱点，不能全部解释成 Kimi-K3 的 CFD 知识不足。普通文本工具操作
与早期漏交还发生在上下文截断之前，所以也不能将所有错误归因于这一个问题。
本批次未修改 FoamClaw、公共提示词、协议或评分规则；改进必须留给新版本比较。

### 事后原生场诊断（不替模型交报告，不改正式成绩）

为了区分报告失败与已有场的质量，试验终止后只读分析了 r-000002 的原生产物，
使用同一冻结基准和数值政策；没有构造/提交模型报告，没有产生正式 evaluation，
也没有把诊断反馈给模型。

| 场 | relative L2 | L2 限值 | relative Linf | Linf 限值 |
|---|---:|---:|---:|---:|
| U | 0.388734 | 0.10 | 0.554632 | 0.50 |
| p | 0.484585 | 0.15 | 0.430469 | 0.50 |

因此，即使只修正报告接口，这份已存在的场也达不到本次固定网格、100 次迭代
的数值复现标准；这不是残留 residualControl 这一静态判据单独造成的结论。
该比较基准不是实验真值或收敛到连续方程的唯一解，不能直接将差异称作物理
意图理解错误。正式失败原因仍为 model_budget_exhausted，正式验收记录数仍为 0。

两次原生运行的所有输入/命令/退出/日志/产物字节和约束都已核对；作业 7941701、
7941703 的释放凭据存在，独立集群查询均不在活动队列。31 条实际工具结果中
未观察到非零工具退出；这不代表其最终报告符合协议。

[完整只读审计](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/review/verified-001.json)、
[事后场诊断](../runs/tutorial-science-matrix-002/trials/s-102/foamclaw/review/posthoc-fields-001.json)。

## 阶段性耗时快照（2026-09-12 20:05:26 UTC，非最终统计）

此时已发 137 次 API 请求，135 条有响应且 HTTP 都为 200；1 条 Codex ReadTimeout
结果不明，另 1 条 FoamClaw 请求正在等待。前一笔 FoamClaw 慢请求已在约 302 秒
后正常返回。以下延迟统计仅针对有 complete 凭据的 135 条，不能把超时静默混入
正常响应分布，也不能将排除超时后的均值称为整批用户体验。

| 指标 | 观测值 |
|---|---:|
| 已返回请求延迟中位数 | 8.929 s |
| 已返回请求延迟 95 分位（线性插值） | 49.006 s |
| 已返回请求最大延迟 | 302.345 s |
| 已返回请求延迟合计 | 2327.225 s |
| 另列的未收到响应超时 | 1 次，600 s 请求等待边界 |
| 已保存原生运行结果 | 5 次（4 成功、1 原生失败） |
| 这些原生命令执行时间合计 | 8.301 s |

API 包括客户端辅助请求。原生执行合计不含集群排队、文件传输和环境准备，
所以不能用两列直接算整批耗时百分比。证据支持当前主要等待发生在模型调用
及其长尾响应，而不是这些小算例的实际数值求解；不据此断定上游具体故障机制。

## s-102 / Claude Code：最终预算耗尽；首次提交缺 AMI 配对信息

第一次 harness 返回用了 25 次 API 调用，有有效运行 action，没有漏交格式反馈。
原生 r-000001 在 blockMesh 阶段退出失败（startup），尚未开始正式求解。
原始清理日志为：

```text
Creating topology patches - from patches section
FOAM FATAL IO ERROR: (openfoam-2306)
No "neighbourPatch" or "coupleGroup" provided.
```

实际 blockMeshDict 采用 `patches ( cyclicAMI AMI1 (...) cyclicAMI AMI2 (...) ... );`
的旧式列表写法，没有两个接口的 neighbourPatch 或 coupleGroup 配对属性。
这不是将反斜杠 n 写成文本导致：该文件有 90 个真实换行、0 个字面量反斜杠 n。

已对照原始 response.raw：submission-01/call-011 中 Write 的 content 与提交
blockMeshDict 逐字相同；call-021 的 controlDict 也逐字相同。因此这处缺字段
首先存在于上游提供的工具内容，不是本地桥接写文件时删除了配对信息。

首次原生执行 0.320 秒，公共约束还记录 unreadable_geometry 和
unregistered_early_convergence。配对缺失由 OpenFOAM 自身独立报出，不依赖
私有几何解析器的这个标签。日志已返回同一会话；以下记录后续修改和最终判定。

[首次运行输入与错误](../runs/tutorial-science-matrix-002/trials/s-102/claude-code/native/runs/r-000001/)、
[原始工具请求和响应](../runs/tutorial-science-matrix-002/trials/s-102/claude-code/agent/)。

### 三次运行与最终状态

| 提交 | 累计 API 调用 | 原生结果 | 实际问题或修改 |
|---|---:|---|---|
| r-000001 | 25 | blockMesh 退出 1，启动失败 | 缺 AMI 配对属性 |
| r-000002 | 56 | 网格两步通过，simpleFoam 退出 -6 | 修好配对；GAMG 的 faceAreaPair 路径不能转换隐式 AMI 组装网格 |
| r-000003 | 64 | 三步均退出 0，完成 100 次迭代 | 唯一输入变化：p 求解器 GAMG / GaussSeidel → PCG / DIC |

第二次的原生错误原文为：

```text
Creating lduPrimitiveAssembly: lduAssembly01
FOAM FATAL ERROR: (openfoam-2306)
Attempt to cast type lduPrimitiveMeshAssembly to type fvMesh
Foam::faceAreaPairGAMGAgglomeration::faceAreaPairGAMGAgglomeration(...)
```

这与 FoamClaw 遇到的是同类 OpenFOAM 配置兼容问题。分类器记 numerical 是因为
已开始打印 U 的求解记录，不代表有证据证明数值发散。第三次确实完成，没有被
预算边界丢弃：新鲜有效的运行 action 被正常执行。但所有 64 次调用已经耗尽，
没有剩余调用来读取第三次运行产物、后处理并正式提交 report。

最终 verdict=fail，reason=model_budget_exhausted；不是 API 故障，也不是
验收器拒收了已正确提交的报告。格式失败 0、正式 evaluation 0、report_failures 0；
后三者不能误读为报告已正确。三次原生执行累计 2.100 秒，模型阶段累计 1399.602 秒。
查询文档 3 次、读取文档 2 次，共返回 10527 字符，包括 cyclicAMI 文档。22 条实际
工具结果未观察到非零退出。64 条 API 都有已知响应，没有异常或输出截断；输入
618256、输出 18459、缓存输入 383628、已报告推理 2607、total 636715，费用未知。

三次运行还都带有 residualControl，公共约束记录 unregistered_early_convergence。
第三次日志实际走到 100，因此不能把这个配置违规标签描述成“运行提前终止”。

### 只读事后场诊断（不是正式成绩）

为区分缺报告与已有场是否接近基准，在该试验终止后对 r-000003 的真实产物作
独立比较；不构造模型报告、不反馈给模型、不修改官方 verdict。

| 场 | relative L2 | L2 限值 | relative Linf | Linf 限值 |
|---|---:|---:|---:|---:|
| U | 0.397322 | 0.10 | 0.562128 | 0.50 |
| p | 0.670640 | 0.15 | 0.578410 | 0.50 |

现存场也不满足冻结的固定网格、100 次迭代复现标准，故单纯替它补报告不足以让
这份产物通过。这不是实验真值比较，不能直接推断它未理解物理意图。正式失败
仍是预算耗尽、尚未交报告，不能把事后诊断冒充模型提交后的验收。

原生输入/命令/退出/日志/产物字节/释放记录均已审计，作业 7941709、7941710、
7941711 经独立只读集群查询均不在活动队列。两个审计凭据均已回读验证哈希。

[三次原生及轨迹审计](../runs/tutorial-science-matrix-002/trials/s-102/claude-code/review/verified-001.json)、
[事后场诊断](../runs/tutorial-science-matrix-002/trials/s-102/claude-code/review/posthoc-fields-001.json)。

## 已结束试验汇总（2026-09-12 20:41 UTC；整批尚未结束）

| 题目 | Codex | FoamClaw | Claude Code | Kimi Code |
|---|---|---|---|---|
| s-101 | 通过；15 调用 | 通过；29 调用 | 通过；41 调用 | 通过；18 调用 |
| s-102 | API ReadTimeout 中断；12 调用，无原生提交 | 失败；64 调用，第二次原生成功，未交合规报告 | 失败；64 调用，第三次原生成功，未交报告 | 运行中 |
| s-103～s-105 | 各 3 项排队 | 各 3 项排队 | 各 3 项排队 | 各 3 项排队 |

合计 20 项：4 通过、2 流程失败、1 基础设施中断、1 运行、12 排队。
本表是带时间的审阅快照，最新状态以顶部实时总表为准。不能用这 7 项提前给
四个 harness 排名；尤其 Codex 的中断项没有测出物理答案，不能算物理错误。

## Claude Code 的调用预算拆分：不是 64 次主解题轮次

逐条检查实际 wire_request.json 的 system 角色与首条用户消息，得到下面的
用途分类。Warmup 会话的首条用户消息确实是 `Warmup`，并非正式题面；命令
前缀和文件路径分析有独立的明确 system 任务。所有这些请求仍使用 Kimi-K3，
不是把预热或辅助分析暗中转发给其他模型。

| 请求用途 | s-101 次数 | s-102 次数 | s-102 输入 token | s-102 输出 token |
|---|---:|---:|---:|---:|
| 主解题会话 | 17 | 25 | 441166 | 7329 |
| 客户端 Warmup 会话 | 11 | 20 | 140566 | 1825 |
| Bash 命令前缀分析 | 8 | 13 | 22876 | 6417 |
| 文件路径分析 | 5 | 6 | 13648 | 2888 |
| 合计 | 41 | 64 | 618256 | 18459 |

s-102 的 39/64（60.94%）请求不是主解题会话。分类只说明实际用途，不断言所有
辅助工作都无用，也不把它们当作模型独立解题采样。其中命令/路径分析还可能由
Warmup 会话内工具操作触发，本表没有额外推测它们所属的父会话。

本批冻结协议是“所有 API 调用都计入 64 次”，所以没有漏记，也不能在看到结果
后给某个客户端补预算。这个结果测量的是包含原客户端启动/辅助机制的端到端
效果；不支持把其预算耗尽简单解释成 Kimi-K3 经过 64 轮物理解题仍不会做。
后续若要比较纯主解题能力，应另建明确协议，而不是修改这批正在执行的条件。

用途审计逐条保存 wire 凭据哈希及原始响应 SHA256；所有 105 条均核对请求/响应
模型标签和 HTTP 200，保存后回读验证哈希。未新增 API 请求、原生命令或评分。

[s-101 请求用途证据](../runs/tutorial-science-matrix-002/trials/s-101/claude-code/review/request-purposes-001.json)、
[s-102 请求用途证据](../runs/tutorial-science-matrix-002/trials/s-102/claude-code/review/request-purposes-001.json)。

## s-102 / Kimi Code：首次运行的真实错误与静态误报分开

截至首次原生提交：23 次 API，1 次缺 action 格式反馈；已搜索文档 5 次、读取
3 次。首请求在 271.720 秒后 HTTP 200 返回，不是超时。首次 r-000001 原生执行
0.321 秒，在 blockMesh 退出失败，未调用求解器。原文为：

```text
Creating topology patches - from patches section
FOAM FATAL IO ERROR: (openfoam-2306)
incorrect first token, expected <int> or '(', found on line 52: punctuation '{'
file: system/blockMeshDict.patches at line 52.
```

实际写法是 `patches ( cyclicAMI AMI1 { neighbourPatch AMI2; ... } ... );`，
混用了旧式 patches 的类型/名称/面列表语法和 boundary 的字典语法。日志与模型
实际提交文件一致，这一启动失败不依赖私有静态约束。日志已返回模型继续修复；
最终结果仍待记录。

### 另一个检查器边界：latestTime 不应强制读取 startTime

该提交的 controlDict 有 `startFrom latestTime;`，没有 startTime。静态检查器
[science_contract.py](../agentcfd_bench/foam/science_contract.py) 第 156～157 行先
允许 latestTime，随后却无条件读取 `control['startTime']`；缺字段触发
unreadable_execution_conditions。这不能当作 OpenFOAM 原生不接受该配置的证据。

固定 v2306 源码 Time.C 的 `Foam::Time::setControls()` 第 143～179 行表明：
仅在 startFrom=startTime 时读取 startTime；latestTime 分支从现存时间目录取值。
当前独立执行环境仅接收 0/ 初场，没有既有非零时间结果。源码 SHA256 为
9dc03a98ba32eb120a4182a9427fdf5f09f1d2ec10772d8178cd92b29053d594，已与
固定原始 tgz 中同名成员逐字节哈希核对一致。

对五题原始配置作纯内存单一语义变体：使用 latestTime、删除未使用的 startTime，
五题原始静态约束均通过、变体均仅因 unreadable_execution_conditions 失败；
五份变体均通过安全输入校验，数值目录只有 0。这确认了检查器过严，未执行
额外原生变体，不能将这个静态复现冒充原生对照。

本题实际首次提交还有独立的网格错误，补上无用 startTime 后静态检查还会继续
发现 residualControl 的 unregistered_early_convergence；因此不据此把整题改为
通过。发现时没有正式 evaluation；native 阶段反馈只包含原生日志、退出分类和
产物，不包含私有 contract。当前未出现由这个标签导致的正式评分反馈，但后续
若进入报告验收，必须专门审计其影响。

本次只增加审计记录，没有修改活动代码、提交、预算或成绩，也没有新付费请求。
修复须建立新的已验证实现边界，不能在进行中的冻结批次内悄悄替换。

[静态反例、实际提交与精确源码依据](../runs/tutorial-science-matrix-002/review/latest-time-contract-001.json)、
[本题首次原生证据](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/native/runs/r-000001/)。

第二次 r-000002：29 次累计调用后提交，模型把 AMI 的字典改为面列表，同时删掉
neighbourPatch/transform。blockMesh 再次失败（0.320 秒），原文变为
`No "neighbourPatch" or "coupleGroup" provided.`。这是修复一个语法问题后暴露
缺失配对信息的第二次真实启动失败。尚未到求解阶段，不称为数值发散。

### latestTime 候选修复的零费用验证（未部署）

候选文件独立保存在 [review_candidates/latest_time_v1](../review_candidates/latest_time_v1/README.md)，
未放入生产包。它只在单独内存模块中应用条件分支：显式 startTime 模式检查
startTime=0；显式 latestTime 模式依靠已验证的仅 0/ 输入，不读取无效字段。
不扩展 firstTime 或省略 startFrom 等其他边界。

75 项静态测试通过，0 失败、0 错误、0 跳过（五题各 15 项）。除正确变体外，
仍验证错误初场/黏度/时间条件、缺场、动态代码和非零结果目录必须拒绝。
运行前后生产源码 SHA256 相同；check_selection 另行核对活动批次所有冻结绑定
仍有效。没有付费 API 或原生求解调用。

这是待部署候选，不是“线上 bug 已修复”或完整原生资格通过。后续仍须原生等价
验证、正式回归与受影响记录审计，并建立新的版本边界，不能覆盖 matrix-002。

[候选实现与测试](../review_candidates/latest_time_v1/check_candidate.py)、
[75 项测试原始凭据](../review_candidates/latest_time_v1/static-tests-001.json)。

### 首次影响范围审计（只读快照，不改分）

使用同一隔离候选，检查当时全部 11 份已完成原生结果和 4 份正式 evaluation：
仅 s-102/Kimi Code 的 r-000001、r-000002 静态标签变化；两份仍因真实网格错误
失败，contract 也仍不通过。补过缺字段检查后会继续发现 residualControl 配置，
不能因删除一个错误标签就认为其他约束均正确。

静态 contract 的通过/失败变化数为 0，正式 evaluation 的内容/结论变化数也为 0。
目前已完成的 4 份正式通过结果未受此问题影响。这是现有记录的影响审计，不是
剩余 13 项未结束/未开始试验的无缺陷保证，也不等于已完成原生候选验证或上线。
所有输入绑定和原正式验收先重放核对，再计算候选结果；官方记录未被改写。

[首次影响审计凭据](../runs/tutorial-science-matrix-002/review/latest-time-impact-001.json)。

### Kimi Code 第三次提交：重复首个网格语法错误，反馈并未丢失

第三次 r-000003 于第 40 次累计 API 调用后提交。它把 AMI 的面列表又换成
`cyclicAMI AMI1 { neighbourPatch ...; faces ...; }`，但外层仍是旧式 patches。
blockMesh 在同一第 52 行再次拒绝左花括号；执行 0.321 秒，仍未开始求解。
不能把它记为三个互不相关的物理错误：目前是两种不兼容配置之间的反复修改。

已审阅 submission-03～06 各自第一条实际 wire 请求，而不是仅看我们本地历史。
第三次运行前的 submission-05 有 88 条消息；原始题面、后处理要求、r-000001
的语法错误和 r-000002 的缺配对错误均保留。第三次之后的 submission-06 有
97 条消息，三份日志全在。解析 feedback 内嵌 JSON 后，日志逐字等于已保存的
原生日志，且没有向模型暴露私有 contract 或参考距离。

因此这次反复不能归因为检查过的请求中缺少上轮 observation。这个结论只覆盖
上述四份请求，不保证之后不会压缩上下文，也不证明模型一定正确理解了日志。
静态 latestTime 误报仍单列；其私有标签没有混入这几次原生反馈。

[实际请求历史核对](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/review/partial-history-001.json)、
[第三次原生输入与日志](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/native/runs/r-000003/)。

第四次 r-000004 在第 48 次累计调用后提交：模型将两处 cyclicAMI 改为普通 cyclic，
又采用旧式 patches 面列表。blockMesh 仍失败（0.320 秒），原生日志明确给出：

```text
Old-style cyclic definition. Splitting patch AMI1 into two halves AMI1_half0 and AMI1_half1
    Alternatively use new 'boundary' dictionary syntax.
```

这不是改用普通 cyclic 后求解成功：仍未进入求解阶段，而且任务要求非共形 AMI。
日志中的 boundary 语法提示由 OpenFOAM 原生产生，已经作为常规反馈返回；不是
主监控 agent 临时添加的解题提示。后续是否利用该提示正确修复仍待实际提交。

[第四次实际输入与原生提示](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/native/runs/r-000004/)。

## s-102 / Kimi Code：最终结果及完整审计

| 指标 | 结果 |
|---|---|
| 生命周期 / 正式结论 / 原因 | completed / fail / model_budget_exhausted |
| 模型 API / harness 返回 | 64 / 14；全部请求有 HTTP 200 响应，未记录截断或 API 异常 |
| 原生提交 | 6：4 次网格启动失败、1 次求解配置失败、1 次完成运行 |
| 提交格式失败 | 8 次，均未产生新 action；其中 5 次在最后运行之后 |
| 合规报告 / 正式 evaluation | 0 / 0；report_failures=0 不代表报告合格 |
| Agent 阶段累计 / 原生命令累计 | 2713.248 s / 3.232 s；后者不含排队和传输 |
| 文档搜索 / 阅读 | 16 / 4；服务返回 50444 字符，无文档请求拒绝 |
| 输入 / 输出 / 缓存输入 token | 2942380 / 25941 / 1903027 |
| 已报告推理 token / 费用 | 180 / 未知 |

所有请求和响应的 model 标签均为 Kimi-K3。这验证请求链路标签，不认证服务商的
实际权重。三条 usage 的 total 各比 input+output 少 7，原样 total=2968300，
input+output=2968321；未改写供应商计数。

第五次在第 56 次累计调用后提交：终于整体改成 boundary 字典，并恢复 cyclicAMI
和 neighbourPatch；blockMesh/checkMesh 均退出 0。但 p 使用 GAMG，在隐式 AMI
的组装网格上触发 `Attempt to cast type lduPrimitiveMeshAssembly to type fvMesh`，
simpleFoam 退出 -6。这与前两种 harness 的 GAMG 兼容错误同类。

第六次在第 59 次调用后提交：仅把 p 求解器换成 PCG，加入 DIC、删掉 GAMG 的
smoother。三条命令均退出 0，实际走到 100 次迭代。但最后连续性误差为
1.1847861e19；已有场的独立提取值如下。

| 实际产物量 | 数值 |
|---|---:|
| 网格内部单元 / 最后迭代 | 24 / 100 |
| 速度 cell RMS | 2.158202e19 m/s |
| 最大单元速度模 | 4.315313e19 m/s |
| 压力单元均值 | -5.812924e39 m²/s²（运动压力，不是 Pa） |
| 最后压力初始 / 最终残差 | 0.97014184 / 0.0059799534 |
| U / p 对固定基准的 relative L2 | 1.702522e19 / 6.397399e39 |

这些不是我们替模型填写的报告。试验结束后仅只读诊断原生产物，没有生成正式
evaluation，也没有反馈隐藏距离。速度量级已明显异常；即使修正 latestTime
静态标签，也不能把这份场判为正确。正式失败仍是未提交报告且预算耗尽。

最后一次运行后，submission-10～13 没有真实工具调用，submission-14 仅调用
Bash 列出产物目录；未执行后处理脚本或写出报告。实际缺 action 快照为
000001、000004、000007、000010～000014，不是我们的评分器拒收了正确报告。
首个普通文本工具标记已出现在 submission-01/call-016 的原始上游响应中，
该请求此前没有这个标记，响应也无正式 tool_calls；模型与上游中间件之间的
成因仍不能从客户端证据拆分，不能都归因于 CFD 知识。

### 客户端与工具观察边界

按 bridge-benchmark-harness 技能核对，实际是 Node 包 @moonshot-ai/kimi-code
0.28.1，而非同名命令的 Python Kimi CLI。其 main.mjs 和 package.json 与本批
冻结哈希一致，没有换成自写循环。

Kimi Code 原生 Bash 工具会提供输出预览，并在截断时附上可读完整日志路径。
抽查的查询输出在实际 wire 中为 2415 字符预览，完整文件仍为 3957 字节，JSON
有效且文档 bundle 哈希正确。该行为可直接定位到已安装 main.mjs 的
BashTool.addForegroundOutputReference；不是 benchmark 新增模型输出 token 上限。
这也不证明模型实际读了完整文件；服务返回字符数不等于模型一定看完的字符数。

59 条 Kimi 工具文本事件没有独立进程退出码，审计脚本只作字面量错误模式扫描；
不能将未匹配到错误写成“已证明所有工具调用成功”。首份审计中过强的自动文字
已[更正说明](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/review/AUDIT-NOTE-001.md)，
以 verified-002 为准；原生审计数据和正式成绩未改写。

六次原生运行的输入绑定、命令、退出、日志、产物字节和释放记录全部复核；
作业 7941713、7941714、7941717～7941720 独立查询均不在活动队列。

[完整原生审计](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/review/verified-002.json)、
[事后场诊断](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/review/posthoc-fields-001.json)、
[客户端身份与输出预览证据](../runs/tutorial-science-matrix-002/trials/s-102/kimi-code/review/client-output-preview-001.json)、
[最新 latestTime 影响审计](../runs/tutorial-science-matrix-002/review/latest-time-impact-002.json)。
