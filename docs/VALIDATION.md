# 迁移验收 — 2026-09-12

## 范围

独立迁移现有 s-001 物理任务、Codex/原生执行适配和必要公共组件。旧改错题库、
judge 和历史成绩未移动；MIGRATION_SOURCES.json 中原始源码哈希复核无变化。
没有启动付费模型评测。

## 测试结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 新项目全套测试 | **130 passed，0 failed，0 skipped**，32.36 秒 | test-results.xml |
| 旧项目相关回归 | **64 passed**，3.16 秒 | science_pipeline / bench_native / harbor_cluster |
| 真实 Codex CLI + 本地假 API | 同一会话、6 次本地请求、2 次提交，最终通过 | test_science_codex_integration.py |
| 真正 namespace/socket 隔离 | 通过，不是 mock 或跳过 | test_codex.py |
| 实际 SIGINT / SIGTERM 与重复取消 | 通过，状态持久化和资源清理 | test_process_interruption.py |
| wheel 构建、独立安装 | 在 /tmp 完成 prepare、demo、report，旧包导入数 0 | dist/ 安装包 |
| 静态发布门禁 | s-001 登记，未登记题 0，模型/原生命令调用均 0 | ci_checks/check_tasks.py |
| 真实 OpenFOAM 对照 | **4/4 通过** | runs/qualification-migration-001/qualification.json |

最早受限沙箱测试曾因 Unix socket 权限失败，已在允许 socket/namespace 的环境
完整重测通过，未隐藏或跳过。旧回归有一个 asyncio_mode 配置警告，64 项均通过。

## 真实 OpenFOAM

| 对照 | 原生结果 | 验收结果 | 原生命令累计秒数 |
|---|---|---|---:|
| 正确参考 | 完整求解至 t=2 | 通过；速度剖面最大误差 0.0008816336652263668 m/s | 3.27889649476856 |
| 缺少 0/U | 启动失败 | 正确拒绝 | 0.5395033792592585 |
| 顶壁错误地保持静止 | 能完整求解 | 物理约束、速度剖面均拒绝 | 0.8015541308559477 |
| 伪造速度报告 | 复用正确运行的冻结输出 | 报告真实性拒绝 | 0 |

上述秒数不包含排队/建环境，不是账单时间。作业 7940801、7940802、7940803
已回收；最终 squeue 查询无活动作业。require_qualified 已重新核验真实证据。

## 冻结身份

- task_digest: `24a8e7b7bbfbc536b44dec9a4e9e436ebcc66babebd338876335ab240d8ba505`
- code_hash: `31a5afb99a0f131d8bc136eae69e8a83aa44dc29a08912aaa36baff5ffde7832`
- reference_hash: `a4c68764f9e26cfe36686149329dbad5cbbbc1fc1ffb555159b960cd590b434b`
- wheel SHA256: `8902916c3907942431fd71af1d649f6105a406b44ff21db91b29ca60fdf54e8d`

安装包不需要旧项目源码；其他机器仍需安装 Codex/Harbor 并配置实际集群环境。
资格绑定当前源码、任务和运行环境，不把本站点结果当作所有部署环境的资格。

## 阅读与复现

演示报告：runs/demo-migration-001/scoreboard.md。3 次假模型调用、2 次运行、
1 次启动失败、最终通过；mode=fake-demo-not-model-score，**不是 Kimi 成绩**。

安装 README 中依赖后，在项目目录执行：

```bash
FOAMCLAW_TEST_CODEX_ISOLATION=1 python -m pytest -q
python -m ci_checks.check_tasks
```

`prepare --qualify-native` 另外执行真实 OpenFOAM 正负对照，不调用模型。
已有资格不需要为查看状态而重跑；report/status 只读。任何付费运行需显式命令。
