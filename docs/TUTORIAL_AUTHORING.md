# 原生 tutorial → 观测重建题：Luna 作者管线

> 2026-09-16 更新：当前未完成出题工作已按用户确认切到 **Sol high**，见
> [当前配置、命令和实时审阅入口](TUTORIAL_SOL_ACTIVE.md)。以下 Luna 配置与试点保留为来源历史。

这条管线准备参考与题目，不是受评 Agent 跑分。作者使用 **GPT-5.6 Luna / Codex CLI**，由主机侧读取 `/root/.codex-experiment` 订阅凭证；凭证不挂入作者或 OpenFOAM 沙箱。既有模型评测入口、s-203/s-204 的验收口径和历史记录均不改变。

```text
原始 v2306 归档 + 515 项清单
       ↓ 归档身份校验、冻结选择（不运行模型）
独立 Luna worker：读原始脚本 → 原生运行 → 物理证据 → 英文题面
       ↓ 每步实时 transcript，native 输入/输出/退出码单独保存
待核验 candidate / needs_support / review / failed
       ↓ 独立证据校验 + 观测导出/评分回放测试
新的不可覆盖发布版本（没有这些证据，不自动发布）
```

## 本轮目标与边界

- 目标是 **100 道合格 query + input + GT**。先排 100 个后续作者尝试，不把尝试数冒充合格题数。
- 保留全部 515 个注册来源。扩展模块、缺依赖、非求解器工具教程、物理存疑题分别记录，不静默移出清单。
- 仅使用原始归档的物理配置。允许照原始 Allrun 执行必要初始化，不允许改变材料、边界、网格或终止条件来凑成功。
- 原始 tutorial 的有限数值解可以作为重建目标；退出 0 **不等于**收敛，更不等于经过实验验证。无需额外的五次重复运行或新网格收敛研究。
- 题面用英文描述物理条件；模型自行建网格和配置。公开几何/观测/单位，原始字典和作者证据私有。参考配置只是一种可行实现，不宣称反问题具有唯一解。
- 作者可使用冻结 docs/源码。此轮作者网络关闭以固定来源；未来受评任务的联网条件需由实验配置明确设置，题面不能代替执行环境开关。

## 文件职责

| 文件 | 职责 |
|---|---|
| `agentcfd_bench/authoring/prepare.py` | 验证归档，冻结来源、示例和作者指令 |
| `agentcfd_bench/authoring/queue.py` | 原生程序可用性检查、按物理类别轮转排队，不做物理判定 |
| `agentcfd_bench/authoring/worker.py` | 复用隔离 Codex/Runner，派发一份作者任务 |
| `agentcfd_bench/authoring/control.py` | 独立后台执行、状态；已派发未知请求不盲重试 |
| `agentcfd_bench/authoring/report.py` | 只读生成中文审阅表 |

配置：`experiments/tutorial-author-luna-v1.json`。作者每题 120 次模型调用，无单次输出 token 上限、无累计 native 时间上限；API 请求 watchdog 是 600 秒。费用与 token 按实际回执记录。两类算例试点 + 一个库开发 worker 并行；按用户后续要求，后续队列改为 **每批 10 题并行，本批结束后自动开始下一批**。它们是工程资源参数，不是新的受评模型预算。

## 命令

在本目录使用 `../.venv-eval/bin/python`。下面 `NEW_DIRECTORY` 必须是带 UTC 时间的新目录；prepare/freeze 绝不覆盖已有实验。

```bash
../.venv-eval/bin/python -m agentcfd_bench.authoring.prepare --config experiments/tutorial-author-luna-v1.json --output NEW_DIRECTORY
../.venv-eval/bin/python -m agentcfd_bench.authoring.control launch NEW_DIRECTORY/campaign.json
../.venv-eval/bin/python -m agentcfd_bench.authoring.control status NEW_DIRECTORY/campaign.json
../.venv-eval/bin/python -m agentcfd_bench.authoring.report NEW_DIRECTORY/campaign.json
../.venv-eval/bin/python -m agentcfd_bench.authoring.queue --pilot-config NEW_DIRECTORY/campaign.json --output NEW_BATCH_DIRECTORY --attempts 100 --parallel 10
```

`queue` 只冻结新队列；`launch` 才消耗模型额度、运行 OpenFOAM。新队列默认等待当前试点结束再派发，避免叠成 13 并发。后台控制器独立于聊天存活，每五分钟或每题结束时保存进度，**不调用主 Agent 来监控**。根目录 `PROGRESS.zh.md` 是中文总表，`progress.latest.json` 是结构化快照。每题 `workers/<id>/agent/transcript.md` 是实时 I/O，`agent/work/REVIEW.zh.md` 是 Luna 完成后的中文审阅说明。

## 不能省略的发布检查

1. 官方归档、原始文件、执行前输入、程序与执行结果必须可以追溯；没有退出证据不能成功。初始化改变必须来自原始工作流，不能凭作者一句“未修改”认定。
2. 实际调用的是目标原生求解器，不是 `postProcess` 或网格命令；字段/维度/终止时间与记录一致。
3. 有限性、网格体积、物理范围、适用的质量/能量一致性和残差/稳态证据必须有原始数值。Luna 的 `passed: true` 只是待验证判断。
4. C/V/物理场来自真实 native 输出；只导出真实存在的场，不给等温题伪造温度。新字段/多区域/颗粒观测不能假装当前固定 U/p/T grader 已支持。
5. 英文题面与几何/观测匹配，已知条件与待推断项清楚；公开包不含原始字典、来源项目名或内部路径。
6. 同一 GT 的独立导出/评分回放为零误差；缺字段、错单位、缺覆盖、NaN、伪造来源等负例拒绝。没有相应测量/评分支持的题保持待审。

当前 `author-result.json` 的 `candidate` **不是 released**，worker 的 `completed` 也不是物理通过。发布器必须基于上述独立证据，不能把作者输出 JSON 当成科学证明。

## 恢复与空间

模型请求已派发但结果不明时保留原始目录并停止该 worker，不自动扣第二次额度重跑。其他独立候选继续执行。只有确认控制器未派发任何 worker 且已经退出时，`retry-unstarted` 才能重新启动，并保留第一次启动失败的日志。

磁盘保留 16 GiB，达到保留线时不启动新的作者/native 操作；已产生的证据不自动删除。剩余候选保持未完成，不能算模型或物理失败。该保留线是启动检查，不是严格的文件系统配额，运行中的输出仍需监控。
