# Workbench v3 工程改造交付与未完成项

> 此页保留首次交付时的状态。后续自由网格验收补齐及新增测试见
> [验收器审阅说明](polyhedral-grader-review.md)，不将历史未就绪结论冒充当前状态。

2026-09-16。没有启动付费模型或四题评测。以下“通过”是工程测试，不是模型成绩。

## 已交付

旧包原样移至 `agentcfd_bench_old/`；旧测试、说明分别移至 `tests_old/`、`README_old.md`。
`archive-v2-inventory.json` 和回归测试验证旧源码未变化。历史 runs、audits、参考版本均保留。

新包职责如下，运行库不导入旧包或事故脚本：

```text
agentcfd_bench/
├── tasks/        公开任务／私有评分资料、YAML、准备与冻结
├── harnesses/    真 Codex CLI、订阅／自定义 API、原生执行 RPC
├── execution/    无网络命名空间、完整原生命令、日志、超时、回收
├── grading/      独立测量导出、GT 比较；旧数值定义单独隔离
├── records/      SQLite 状态、追加式 I/O、不可覆盖退出收据
├── reports/      只读统计，不执行模型或补算
├── controller.py 有限预算、同一会话、恢复
└── cli.py        prepare / run / resume / status / report
```

### 运行与反馈

- 解题环境只挂载本题 public、工作区、离线 docs、自身的只读输出。凭据留在宿主代理。
- 原生执行环境独立、无网络，不挂载 GT、grader 或凭据。使用完整安装中的命令和库，不按字典关键词拒绝表达式、函数对象或库名。
- `exec` 支持脚本、网格和检查；`run` 直接选择安装的原生程序；`status/logs/cancel` 操作同一个运行 ID；`submit` 是明确的最终提交。
- 日志不再先被转换为粗粒度“配置不合法”。保留原始 stdout/stderr、退出码、失败现场和超时前写出的场。
- 每次操作冻结工作区；原生输出只读返回。下一次操作前，Agent 显式复制需要的结果，不偷偷替换网格或初场。
- 每题累计 64 次模型请求、1000 秒 Agent 原生命令用时；不新增单次输出 token 上限。真实耗量作为统计。测量导出用时单列。
- GT 评分不是可反复查询的交互工具。实时 transcript 保存可捕获的公开解释、搜索命令、返回内容、动作与日志；不补写隐藏思维链。

### 本轮实际抓到并修正的工程问题

| 问题 | 修复／验证 |
|---|---|
| 原生运行包只覆盖部分工具 | 补齐 314 个可执行文件；逐个扫描动态依赖 |
| snappyHexMesh 库搜索路径不足 | 加入原安装的 dummy 分解库路径；真实启动通过 |
| setSet 缺 libreadline.so.6 | 从同一原运行环境补齐兼容依赖；真实启动通过 |
| Astra 元数据仍暴露多 Agent 工具 | 保存原模型目录，再显式关闭模型目录中的 v2 delegation；测试检查实际发出的工具定义 |
| 遗漏传输统计模块 | 两种真实 CLI 的本地假 API 测试发现并修复 |
| shell 查 docs 被旧 RPC 统计显示成 0 次 | 不再把旧 RPC 计数当文档使用次数；实际搜索保留在 transcript，次数未知时记 unknown |
| 非法 RPC 可能 KeyError／BrokenPipe | 明确校验请求，返回结构化错误；拒绝非有限 JSON 数值 |
| 求解退出后回收中断可能重复启动 | 先保存退出收据；回收从原现场继续，不重新启动求解器 |
| 二进制原生字段被文本提取器跳过 | 独立沙箱内用原生格式转换，再提取；ASCII／binary 两条真实链路都测过 |
| 状态投影过时影响报告 | 报告只读事务库的已提交状态，不将旧 status.json 当调度事实 |

## 测试证据

`docs/v3-tests-final.xml`：**67 passed，0 failed，0 skipped，111.28 秒**。

- 真正的 Codex CLI + 本地假订阅 API，以及真 CLI + 本地假自定义 API；不使用实际订阅或 API 额度。
- 同会话恢复、工具读写、离线 docs、没有公网／GT／宿主目录、没有子 Agent 工具、没有新增 token cap。
- 实际 OpenFOAM 工具启动、字典原生报错，以及 400-cell s-205 的网格、初始化、求解、独立导出和 GT 比较。
- ASCII 与 binary 两种实际输出路径；参考字段缺失不通过；四题原 GT 的只读数值重放；错误场不通过。
- 假模型的 pass/fail、未知 API 请求不重发、已保存响应恢复、不重置调用预算、已完成不重复评分。
- 真实进程失败、超时、取消、退出后回收恢复、只读产物、防路径越界、旧档案完整性。

动态依赖扫描见 `docs/native-dependency-audit.json`；缺失项为零。
环境 manifest 记录实际内容指纹。当前已验证串行原生命令；不宣称已验证动态 C++ 编译、跨节点 MPI 或强 cgroup 总资源配额。

## 不能声称四题已正式就绪

当前 `prepare`：`engineering_ready=true`、`ready=false`。这是主动阻止把验收器的表示限制当作模型失败，不是新的 GT 求解计划。

| 任务 | 仍需从旧验收中消除／验证的假设 |
|---|---|
| s-202 | 材料区域、开口和接触面的旧命名绑定；五区域实际输出的完整新导出链尚未集成重放 |
| s-203 | inlet/outlet 等旧 patch 命名绑定；任意网格跨观测分区的积分准确性尚未验证 |
| s-204 | 提取器目前重建 Cartesian 张量网格；壁面统计仍绑定旧 patch 名 |
| s-205 | 轴向统计目前假定单个单元跨越整个截面；一般 polyhedral 网格尚未支持 |

因此：本次完成了执行骨架与档案隔离，不把旧数值提取器搬到新目录就宣称“完全自由网格验收已完成”。
下一步应只改 grader 的几何积分与物理区域映射，用相同原生场的重命名、重排、不同网格表示做对照测试，再解除准备门。
无需重新运行四题 Ground Truth；原专家接受的参考、误差阈值与“收敛诊断不作新增硬门槛”的评分口径保持不变。

## 快速代码审阅入口

1. `harnesses/codex.py: PROTOCOL / Codex.run`：模型究竟收到什么、如何接接口。
2. `execution/sandbox.py: Sandbox.command`：实际挂载、网络及原生工具路径。
3. `harnesses/tools.py: ToolServer.call`：Agent 能调用哪些操作，不能查询什么。
4. `execution/worker.py: execute / collect`：退出、保存证据与恢复的顺序。
5. `grading/service.py: grade_submission` 与 `grading/evaluate.py: evaluate`：测量和评分的边界。
6. `tests/test_codex_local_api.py`、`tests/test_native_openfoam.py`、`tests/test_controller.py`：正常／失败／恢复的可运行例子。
