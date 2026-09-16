# Astra xHigh 四题正式实验：启动记录

实验目录：`runs/workbench-v3/20260916T022031.171364Z-1ff93ae2`。

- 后台控制器 PID：1539252；独立进程会话，启动收据见实验目录 `launch.json`。
- 账号：仅 `/root/.codex-experiment`；Codex + `gpt-6-astra` / `xhigh`，禁用子 Agent。
- 任务顺序：s-205 → s-203 → s-202 → s-204，串行。
- 每题 64 次模型调用、1000 秒原生计算；网络请求超时 600 秒。没有额外 token 总量／输出上限。
- 解题环境不联网，只能查询冻结 OpenFOAM 文档；原生运行与私有评分隔离。
- 配置：`experiments/workbench-v3-astra-experiment-account.yaml`。
- 题目版本：`tasks/releases/workbench-v3-polyhedral-v2`。
- 准备检查：`ready=true`，无 blocker；资格证据绑定 grader 代码与参考观测。
- 启动前整套工程回归：142 项全部通过，0 失败、0 跳过。不是模型得分。

2026-09-16 02:21 UTC 的首次运行观察：s-205 已进入运行；捕获 3 次模型请求、0 个接口错误；
已实际执行读取几何、查询文档路径和查询 OpenFOAM 提交接口，相关命令退出码为 0。
其他三题排队。这里只记录启动时事实，后续动态结果以状态库为准。

## 自己查看实时进展

```bash
cd /root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench
../.venv-eval/bin/python -m agentcfd_bench report runs/workbench-v3/20260916T022031.171364Z-1ff93ae2
tail -F runs/workbench-v3/20260916T022031.171364Z-1ff93ae2/trials/s-205/transcript.md
```

每题 `transcript.md` 是实时中文栏目 I/O 记录；`native/r-*/stdout.log`、`stderr.log` 是原生输出；
`grading/result.json` 是最终私有评分。顶层 `controller.log` 主要记录控制器完成／异常，
不要只用它判断 Agent 是否还在工作。`calls` 状态在完整 Harness 返回时入账，过程请求见实时 transcript。

后台会自行进入下一题，不需要主 Agent 留在循环里驱动。遇到结果不明的请求不会自动重发；
基础设施中断不能当作物理失败。请勿重复运行 `run` 来“查看进度”，它会启动新实验。

收敛语义：本轮仍对照专家接受的有限精度 GT，保留原误差范数和阈值；
`convergence_certified=false` 不等于没有评分，而是没有额外声称已证明连续解／网格收敛。

修复详情与 s-202 的旧后处理偏差见 `docs/polyhedral-grader-review.md`。旧参考与历史实验均保留。
