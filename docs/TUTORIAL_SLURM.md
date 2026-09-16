# Tutorial 作者任务的 sca2070 执行层

Luna/Codex 继续在本地通过 `/root/.codex-experiment` 调用；只有 native 操作交给 SSH → Slurm → Apptainer。作者拿不到 SSH 密钥，远程容器看不到宿主工作目录、账号目录或其他任务。

## 写入边界

本次所有新远程文件位于：

```text
/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/authoring/20260916T082025Z/
  runtime/       # 本次独立的 314 程序运行环境
  operations/    # 每次 native 操作的输入、脚本、日志、退出回执与输出
  shared-*/      # 一次 64 核 allocation 的队列、step 回执、心跳和资源状态
```

源软件 `/public3/home/sca2070/software-sca2070-bak/OpenFOAM/dev/OpenFOAM-v2306` 只读。新环境复制其完整编译程序和库，沿用已有隔离包的外部依赖；不改旧实验、软件安装、其他工作目录。

## 代码与接口

| 文件 | 职责 |
|---|---|
| `authoring/slurm_runner.py` | 保持既有 `start/status/logs/cancel/verify` 工具协议 |
| `authoring/slurm_transport.py` | 独立上传、单次提交、观察、增量日志、校验后回收 |
| `authoring/slurm_job.py` | 计算节点隔离执行，退出先落盘、再打包输出 |
| `authoring/slurm_pool.py` | 一个 64 核 allocation 内最多 10 个独占单核 srun step |
| `authoring/shared_node.py` | 准备共享队列、心跳、排空后释放；准备本身不申请节点 |
| `authoring/stage_slurm.py` | 在批准目录新建完整运行环境，不覆盖已有环境 |
| `authoring/probe_slurm.py` | 不调用模型的真实远程联通/失败/隔离测试 |
| `authoring/probe_shared.py` | 验证同一节点、10 路重叠、不同 step/CPU、原始 OpenFOAM 成败 |
| `authoring/migration_gate.py` | 锁住未开始的题，当前题完成后退出旧控制器，不伪造派发记录 |
| `authoring/migrate_slurm.py` | 仅迁移未派发题，保留原注册分母、模型、账号、预算和历史 |

作者配置通过 `native_backend: ssh-slurm` 和 `remote` 对象选择远程后端；既有默认 local 行为不变。模型/题面/预算不因为传输层切换而重置。未知 SSH 提交结果只能查找原作业，不能直接重复 sbatch。

`exit.json` 已有但输出还没收完时不是通过。Slurm 的 `COMPLETED` 也不等于 native 成功：故意返回 7 的测试已确认 native 错误能独立保存，即使外层 Slurm 脚本正常结束。

## 一个节点怎样跑十题

```text
本地 Luna 作者控制器（每批 10 题，账号 /root/.codex-experiment）
  └─ SSH 投递每题独立 native 操作
       └─ sbatch：1 节点 × 64 核，只申请一次
            ├─ srun：1 CPU → 独立 Apptainer → 算例 A
            ├─ srun：1 CPU → 独立 Apptainer → 算例 B
            └─ ... 同时最多 10 个 step，其他操作排队
```

每个 step 使用 `--exclusive --exact --ntasks=1 --cpus-per-task=1 --cpu-bind=cores`。
这是**题间并行**，不是每题自动用 64 核，也不擅自将原 tutorial 改成 MPI。
申请 64 核是集群分配粒度；此版计算进程最多占 10 核，尚未追求用满 64 核。
每个 step 预留 4 GiB，节点 allocation 预留 64 GiB。

第一个 native 操作到来才申请节点。控制器每 5 分钟更新进度和心跳；全队列结束后
通知远程排空已投递的步骤并退出 allocation。控制器失联且没有排队/运行步骤时，
30 分钟无心跳自动释放。正在运行的步骤不因主 Agent 离开而终止。
单个未知提交不会重发；共享 allocation 意外退出也不会静默另申请一台重跑。

## 实际验证证据

- 本地针对性测试：47 项通过，包含路径边界、归档安全、哈希、退出但未回收、提交不重发、恢复发现与既有工具协议。
- 真实远程：隔离检查、预期退出 7、原始方腔 blockMesh/icoFoam 共 4 项通过，0 次模型请求。
- Slurm 作业号分别为 7956444、7956443、7956450、7956451；真实方腔终点 0.5 的 U 字段已回收校验。
- 旧远程实现全量回归 288 项通过：`docs/tutorial-slurm-tests-20260916.xml`。
- 新共享池实测：作业 **7956677**、节点 **ed0506**、`AllocCPUS=64`；前 10 个 step
  同时运行，实际 CPU 亲和性分别覆盖 0–9，无重叠。其后 4 项 native/隔离检查仍复用该 allocation。
- 同节点测试含预期退出 7 的失败路径，不将它误记成 native 成功；0 次模型调用。
- 此测试 allocation 已正常结束并释放。记录：
  `runs/tutorial-authoring/20260916T075646Z-luna-batch10-v1/remote-migration-001/shared-probe-001/qualification.json`。
- 新共享实现全量回归 **297 项通过**：`docs/tutorial-shared-node-tests-20260916.xml`。
  此后新增的退休保护 2 项、过载冷却/恢复 3 项也在针对性回归中通过。

## 当前迁移与查看入口

原本地队列注册 100 题。已开始的 10 题保留原记录，**剩余 90 题**迁到：
`runs/tutorial-authoring/20260916T084800Z-luna-sca-shared10-v1/campaign.json`。
这不是缩小分母；新报告链接回原队列，完整来源注册表仍保留 515 条。
模型交互已经结束但 native 仍运行的两个原题，不因迁移而被取消、重复或宣称通过；
其路径/进程身份保存在迁移目录的 `controller-retirement-intent.json`。

在 `AgentCFD_Terminal_Bench` 下使用：

```bash
# 唯一一次后台启动；已启动后再次执行会拒绝，避免重复模型请求
../.venv-eval/bin/python -m agentcfd_bench.authoring.control launch runs/tutorial-authoring/20260916T084800Z-luna-sca-shared10-v1/campaign.json

# 只读当前状态
../.venv-eval/bin/python -m agentcfd_bench.authoring.control status runs/tutorial-authoring/20260916T084800Z-luna-sca-shared10-v1/campaign.json

# 可读进度由后台自动更新，模型结束不等于科学资格通过
less runs/tutorial-authoring/20260916T084800Z-luna-sca-shared10-v1/PROGRESS.zh.md
tail -F runs/tutorial-authoring/20260916T084800Z-luna-sca-shared10-v1/controller.log
```

每题实时 IO 在 `workers/<题号>/agent/transcript.md`；native 回执、日志、Slurm job/step ID
在 `workers/<题号>/native/r-*`。本次原生检查仅验证远程执行桥接，不代表 100 题已经发布。

### 上游过载的调度处理

新队列启动时实际收到 `response.failed` / `server_is_overloaded`。这不是 Slurm 故障，
也没有证据说明是账号额度耗尽。为阻止连续派发，已锁住未开始的题，在当前交互结束后
切换至 `author-provider-overload-v1` 调度：上批存在明确过载回执时，后台冷却 600 秒再发
下一批；冷却截止时间持久化，恢复不重新计时。不把失败请求当作成功，也不盲目重复已有
请求；已结束但未产出材料的题仍需后续独立恢复/复核，不冒充完成百题。

`resume-known` 仅在原控制器已结束、所有已派发交互都有终止回执时允许接续未开始题。
本次接续日志为 `controller.resume-001.log`，`PROGRESS.zh.md` 始终是最新可读入口。
