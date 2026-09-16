# Astra 联网双题并行启动记录

2026-09-16 UTC，按用户要求停止旧离线轮，重新启动两项独立联网实验。
旧目录 `runs/dense-reconstruction/20260916T044204.828230Z-b42ee030/` 保留全部证据：
s-204 停在已派发 71 次请求，s-203 尚未派发；控制器与当时原生作业均已终止。
`cancellation-result.json` 为停止收据，旧成绩没有覆盖。

## 新任务

| 任务 | 运行指纹 | 初始控制器 PID |
|---|---|---:|
| s-204 自然对流 | `20260916T053642.688204Z-f6d46f68` | 1649417 |
| s-203 分岔流 | `20260916T053705.904691Z-f87424c3` | 1650065 |

目录均位于 `runs/dense-reconstruction-web/`。两项任务的控制器已同时存活，
实际模型请求均获得官方服务 HTTP 200；不依赖主 Agent 保持会话。
每题 120 次模型调用、原生计算不限时，Astra xHigh 使用 `/root/.codex-experiment`。
保留单次 API 故障保护、工作区隔离和冻结 GT 评分；不启动新的 Kimi 任务。

## 已验证真实联网，而非只打开配置

两题均已经主动调用原生网页工具，官方搜索返回 HTTP 200。

- s-204 搜索闭腔质量／压力处理，随后打开 OpenFOAM v2306 `buoyantSimpleFoam/pEqn.H`，
  并查询 Betts–Bokhari 浮力腔体的边界温度和湍流设置。
- s-203 搜索 Arrhenius 黏度、`scalarTransport` 的扩散参数和不可压缩黏性耗散温度源项。

原始关键词与实际返回资料已在各自 `trials/<task>/transcript.md` 实时落盘；
返回资料不等于模型已正确理解，最终物理得分仍须独立验收。

```bash
tail -F runs/dense-reconstruction-web/20260916T053642.688204Z-f6d46f68/trials/s-204/transcript.md
tail -F runs/dense-reconstruction-web/20260916T053705.904691Z-f87424c3/trials/s-203/transcript.md
```

各目录含 `experiment.yaml/json`、冻结代码、公开／私有任务快照、状态库与原始收据。
状态库的 `calls` 可能到当前 CLI 轮结束才结算；实时模型派发应数
`calls/turn-*/api/call-*/dispatch.json`，搜索单独在 `api/web/*/dispatch.json`，不能混算。

工程验收：全套 240 项通过，无失败／跳过；另有 37 项报告／搜索／恢复定向回归通过（与全套有重叠，不相加）。
详见 `web-research-full-tests-20260916.xml`、`web-research-report-tests-20260916.xml`。
本轮不修改评分口径；联网成绩与离线成绩分开记录。
