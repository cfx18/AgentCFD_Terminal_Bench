# AgentCFD Bench — isolated OpenFOAM workbench v3

新的主入口是 agentcfd_bench。旧实现原文保存在 agentcfd_bench_old，旧测试在 tests_old，
旧说明在 README_old.md；历史 runs、audits 和题目版本没有被覆盖。新包不导入旧控制器。

原执行骨架的交付记录见 [工程交付清单](docs/v3-refactor-review.md)。
自由网格验收的后续修复、原生回放及 GT 后处理差异见
[验收器审阅说明](docs/polyhedral-grader-review.md)。旧任务版本仍保持未就绪；
新实验使用有独立资格证据的 `workbench-v3-polyhedral-v2`，不直接翻转旧版本的放行标记。

本轮整套工程回归：142 项通过，0 失败／跳过。四题正式实验已独立启动，
查看 [启动记录与实时监控命令](docs/astra-polyhedral-launch-20260916.md)。工程测试通过不等于模型通过。

## 流程与职责

```text
公开 Query + geometry → Codex/Astra + 离线文档／明确启用的网页检索
                            ↕ exec / run / status / logs / cancel
                    无网络的原生 OpenFOAM 环境
                            ↓ 显式 submit(run_id)／登记的调用耗尽收尾
                    冻结原生结果 → 私有 GT grader → 只读报告
```

| 代码目录 | 唯一职责 |
|---|---|
| agentcfd_bench/tasks | 版本化公开题面和私有评分资料；实验 YAML |
| agentcfd_bench/harnesses | 真正 Codex CLI / Node Kimi Code，会话、订阅／自定义 API、公开工具接口 |
| agentcfd_bench/execution | OS 隔离、原生命令、预算、实时日志、失败现场、恢复 |
| agentcfd_bench/grading | 从原生结果独立提取量、GT 误差、明确登记的收敛条件 |
| agentcfd_bench/records | SQLite 状态、不可覆盖收据、实时中英文 I/O 轨迹 |
| agentcfd_bench/reports | 只读统计；不调用模型、求解器或补算分数 |

模型只能看到本题公开文件、自己的工作区、离线文档和自己的只读结果。
模型凭据留在宿主代理；默认只转发模型请求。显式联网模式增加固定的官方搜索接口，
不提供通用互联网代理，也不开放 shell／求解器的公网。
解题环境不挂载 GT、grader、宿主目录、其他任务或以往成绩。原生运行环境也不挂载这些内容。

新增正式轨道：[稠密观测重建：自然对流与分岔流](tasks/releases/dense-reconstruction-v1/README.md)。
该轨道**有意公开目标场的数值观测**，不公开原始配置与私有验收实现；它测重建能力，不是隐藏 GT 预测。
正式版已冻结用户确认的分阶段 reward，并绑定真实跨网格采样、完整性检查与测试证据。
原 [草案记录](task-drafts/dense-observation-v1/README.md) 保留，不通过翻转旧草案标记来发布。
上面的“GT 不挂载”指原有隐藏参考轨道；公开观测轨道的目标 CSV 是公开输入，提示词也相应区分。
本草案接入后的全套工程回归：142 项通过，0 失败，包含 51 项新增稠密观测测试；
无付费模型调用。[本轮测试记录](docs/dense-reconstruction-full-20260916-002.xml)。

## 使用

Python 3.12，四题实验配置：experiments/workbench-v3-astra-experiment-account.yaml。
该配置明确使用 `/root/.codex-experiment` 的订阅账号、Astra xHigh，禁用子 Agent。

官方 Kimi 的独立配置为 `experiments/workbench-v3-kimi-official.yaml`：
Node `@moonshot-ai/kimi-code@0.28.1` + Moonshot `kimi-k3`，不用 Python kimi-cli 或中转站。
两份配置共用题目版本、离线文档、原生环境及预算，但不共用会话／工作区／运行目录。
该桥接读取宿主 `.env.kimi-official`，只向匿名环境提供占位凭据；
正式密钥不进入配置快照或 Agent。见 [Kimi 接线与启动记录](docs/kimi-workbench-launch-20260916.md)。

```bash
python -m agentcfd_bench prepare experiments/workbench-v3-astra-experiment-account.yaml
python -m agentcfd_bench run experiments/workbench-v3-astra-experiment-account.yaml --allow-paid
python -m agentcfd_bench resume /absolute/run/directory --allow-paid
python -m agentcfd_bench status /absolute/run/directory
python -m agentcfd_bench report /absolute/run/directory
python -m agentcfd_bench regrade /absolute/run/directory s-204
```

prepare 不调用模型、不做完整求解。未通过环境／资料／评分准备检查时，run 拒绝启动。
每次 run 创建独立 UTC 时间目录，包含配置、代码、文档、任务快照及后续所有输出。
resume 要求与该运行冻结代码一致，不能用修改后的当前源码继续旧实验。

`regrade` 是明确的验收器修复回放入口：只接受已结束、已显式提交的题，拒绝与活动控制器并行。
它使用原题目、原 GT 和原提交结果，用当前验收器重新导出测量并评分；不调用模型、不推进求解时间。
原评分和冻结代码不变；新评分、代码快照和前后状态保存在 `trials/<task>/regrades/<UTC指纹>/`，
完成后更新事务状态，`status/report` 显示新结论并保留重验收记录位置。

稠密重建结果使用 `dense-result-v2`，区分三个概念：

| 字段 | 含义 |
|---|---|
| `metric_reward` / `field_scores` | 独立采样后的 GT 匹配分与逐场误差；即使来源待审也保留，不是正式成绩 |
| `eligibility` | `eligible` 可评分、`invalid` 已确认无效、`review` 待审、`error` 验收基础设施异常 |
| `reward` | 可评分时等于匹配分；已确认无效记 0；待审或基础设施异常为 `null` |

原有归一化尺度、RMSE／最大误差阈值及取最差场规则不变，`pass` 仍代表满分。
初始输入允许省略 OpenFOAM 的可选 `location`；独立测量的输出字段检查不放宽。
原生能量方程和结束运行的控制器按实际行为审计，不因其不是采样工具而误拦。
重启须有更早派发的原生计算、对应时刻日志及完全一致的加载文件哈希；随机运行 ID 不表示时间顺序。
完整修复、复评分数与证据索引见 [稠密 grader 修复审阅](docs/dense-grader-v2-review-20260916.md)。

修改 grader 不会自动更新旧任务的资格证明或实验快照。旧冻结实验继续使用其冻结代码；
使用新 grader 启动新实验须另发有资格证据的任务版本，不能直接篡改旧版 `qualification.json`。
上述 `regrade` 是本轮明确授权的已有提交修复回放，不等于启动新实验。

总模型调用默认 64；所有 Agent 请求的原生操作共用 1000 秒。没有额外 token、费用、
提交失败次数上限。每次请求的 600 秒是网络故障保护，不是模拟物理时间。
评分器仅为测量导出的计算另记 grader_native_seconds，不推进物理时间、不占用 Agent 预算。

### 稠密重建：120 次调用、不限解题用时

新配置：[dense-reconstruction-astra-120.yaml](experiments/dense-reconstruction-astra-120.yaml)。
沿用 Astra xHigh、`/root/.codex-experiment`、s-204／s-203、离线文档及已批准的 GT 和评分阈值。
旧 64 次／1000 秒配置、冻结运行和成绩保留，不混合比较。

```yaml
budget:
  model_calls: 120
  native_seconds: null
  request_seconds: 600
completion:
  on_model_budget_exhausted: evaluate_latest_successful
```

`null` 表示取消累计原生用时和整个 CLI 进程的墙钟期限；未指定单次命令期限时也不限时。
保留单次 API 无响应保护、内存／文件大小安全限制，以及 Agent 自己指定的命令期限。
耗时、token 与费用仍是统计量；不存在额外输出 token 上限。验收采样本身的故障保护仍保留，
其失败是验收基础设施异常，不是模型物理错误。

到调用上限后，**不因没有 submit 自动记零，也不额外调用模型写总结**：

1. 有明确提交就验收该结果；否则等待已派发的原生操作结束。
2. 按持久化派发顺序选择最后一个正常退出的 `run`，不看 GT 挑最高分。
3. 冻结选择，交给同一个验收器独立采样和计算原有连续 reward；短诊断运行仍须满足题目终点要求。
4. 记录 `stop_reason=model_budget_exhausted`，与物理 verdict／reward 分开。

失败、取消及 `exec` 不作为自动候选。没有成功计算时明确报告 `no_successful_native_output`；
缺失退出证据或文件损坏记为 error，不能伪造通过、补发未知请求或偷偷换用更早答案。
不限时意味着真正挂住的原生作业仍可能需要人工取消，管线不会偷偷追加时间上限。

审阅文件：`trials/<task>/transcript.md` 为实时可见 I/O；
`finalization/selection.json` 为选择依据；`finalization/summary.json` 为确定性结果摘要；
`grading/result.json` 为独立物理评分。摘要不是补写的 Agent 推理或新答案。
恢复只观察原操作、读取已有收据；重验收只能复用已冻结的选择，不能重新选答案。

准备检查不调用模型；正式启动会使用订阅并产生新的时间指纹目录：

```bash
python -m agentcfd_bench prepare experiments/dense-reconstruction-astra-120.yaml
python -m agentcfd_bench.launch experiments/dense-reconstruction-astra-120.yaml --allow-paid
```

实现与本地验证说明：[调用预算收尾](docs/budget-finalization-120.md)。

### 联网重建：两题独立并行

用户批准的联网重测使用 `network: web-search-live`，通过真正 Codex 原生网页工具检索、
打开公开资料；Astra 的 Responses Lite 模式使用独立 `alpha/search` 接口。
该模式目前只支持 Codex 订阅桥接；自定义 API 的原离线接口保留，不谎称已支持联网。

```bash
python -m agentcfd_bench.launch experiments/dense-reconstruction-astra-web-120-s204.yaml --allow-paid
python -m agentcfd_bench.launch experiments/dense-reconstruction-astra-web-120-s203.yaml --allow-paid
```

两条命令各自启动脱离终端的控制器，可接连执行；两题同时运行，不共享会话、目录、
120 次模型调用预算或原生结果。每题不限原生计算用时；共用订阅可能受到服务端限流。
旧离线轮保留，不把联网结果混入离线统计。输出根目录为 `runs/dense-reconstruction-web/`。

联网工具请求、搜索词、URL 和服务端实际返回文本在发生时写入 `transcript.jsonl/md`，
原始响应另存于 `calls/turn-*/api/web/*/`。模型还被要求写简短公开笔记，说明检索所得
如何影响决策；不能把返回资料当成已采用知识，也不补造未公开的内部推理。
独立搜索是工具操作，不另扣模型生成次数；搜索次数、耗时与模型调用可分别审计。
Codex 自带的搜索返回长度参数原样保留，不对模型生成新增 token 上限。
公开教程也允许检索，故这是 **open-web / reference-assisted** 条件，不宣称闭卷物理推理。

### 原生工具不再被字典白名单限制

Agent 通过 python3 /opt/foamctl.py 使用：

```text
exec -- blockMesh
exec -- checkMesh
exec -- bash prepare.sh
run -- pimpleFoam
status r-...
logs r-... --stream stderr --offset 0 --size 16000
cancel r-...
submit r-...
```

所有镜像内原生工具／库可用，不限制特定 solver、函数对象、参数或表达式。
exec 是自由准备／检查命令；run 由执行服务直接调用模型选择的已安装原生程序，
避免把用户编写的脚本回显当成求解器完成证据。脚本可通过 exec 运行。
每次操作冻结 /work。前处理生成的文件在 /artifacts/<id>/，下一次操作前由 Agent
复制所需文件回 /work；不偷偷在下一轮重建网格或重置场。

错误、超时、取消都保存完整 stdout/stderr、真实退出原因、已写出的场。status 可在运行中查询，
logs 可分页读取。只能对本题操作取消。未知启动／API 请求不会盲目重发。
正式提交后不向 Agent 返回隐藏 GT 值或误差位置；正式结果不能由其后处理覆盖。

## 评分状态必须诚实

示例：

```json
{"verdict":"fail","reason":"physical_acceptance","checks":{"native_completion":true,"reference_match":false},"convergence_certified":false}
```

迁移保留四题已获专家接受的 GT、既有数值误差阈值和物理场合法性检查。
旧规则中的 task_contract、配置模板匹配、输入工具白名单不进入新执行链。
收敛检查是独立规则；未登记的收敛阈值不会被臆造，GT 接近不能冒称连续解已收敛。
旧任务版本的提取器仅支持特定网格表示；新版本按真实多面体与物理观测区求交，
按几何位置识别壁面，支持区域改名／拆分。特殊表示若不能可靠处理，仍必须记为
grader_mesh_representation_unsupported / error，不能记模型失败。
准备门绑定已测试的评分代码、参考观测版本与资格证据，不能只改 qualified=true 放行。
参考原始求解场不变；s-202 的旧中心分箱存在后处理偏差，已在独立的新观测版本修正，
其他三题的变化仅为浮点舍入量级。既有误差范数与阈值没有放宽。
已有专家接受的有限精度 GT 口径不变：收敛诊断仍不是新增硬门槛，不要求专家重新批准原参考。

## 测试

```bash
python -m pytest -q tests
```

包含真实 bubblewrap 隔离与进程测试、假模型／本地假 API、原生 OpenFOAM 接口检查、
历史 GT 原生字段只读重放。绝不将旧测试总数称为新主流程的测试成绩。
历史工具需要历史冻结代码；不要将旧 ci_checks 当作 v3 入口。

新增任务：public/ 只包含题面与输入；private/ 登记参考、指标与阈值。新增 grader 只处理
冻结输出，不依赖执行调度、不调用模型。新增执行后端实现相同收据／隔离约定，不复制评分逻辑。

Codex 会话和非交互接口遵循官方说明：https://developers.openai.com/codex/noninteractive/ 。
传输与实时记录代码由旧实现迁移保留在 harnesses/_transport，其自身不包含旧任务调度器。
