# Kimi Code + Kimi-K3：四题独立重测

用户授权与 Astra 同时运行，不修改已有 Astra 配置、快照或成绩。
配置入口为 `experiments/science-kimi-code.yaml`，实际客户端是已安装的
`@moonshot-ai/kimi-code 0.28.1`，不是 Python Kimi CLI。

## 对比条件

- 两轮均为 s-205 → s-203 → s-202 → s-204，`expert-output-v1`。
- 相同英文公开题面、几何、GT、误差阈值及独立 OpenFOAM 执行。
- 均不评估 `task_contract`；保留原生执行、场合法性、GT 与报告一致性检查。
- 每题累计 64 次实际模型请求；累计／单次原生预算均为 1800 秒。
- 相同只读通用 OpenFOAM 文档；不能联网、查看教程答案、GT 或评测代码。
- 各控制器内部串行；两个控制器可以同时运行，原生提交使用独立集群租约。
- Kimi 使用既有宿主 `.env` 的自定义 API；Astra 使用 Codex 订阅。
  不复制凭据、不自动改模型，也不忽略中转站错误。
- Kimi 保留其原生提示、工具与上下文机制。Codex 专属的附加中文决策摘要
  在 Kimi 上为关闭；两者均实时捕获 I/O。Kimi 配置的上下文窗口为 131072，
  本管线不注入单次输出 token 上限，但保留客户端／提供方自己的设置。

这是两个模型＋harness 组合的对比，不是单独测量 harness 差异。

## 验证和命令

只扩展原有 `probe_codex_client.py` 的显式 `--harness` 选择；默认仍为 Codex。
不改实际 Agent 循环、评分器或 Astra 冻结版本。
静态技能 helper 的旧 `bridge_missing` 提示不作为运行结论；实际适配以
`smoke/agent.py`、客户端包身份和本轮本地／在线接口证据为准。

本轮证据在 `audits/kimi-output-reference-20260916-001/`。
本地测试通过后，用最多 6 次请求执行真实 Kimi Code 文件／文档接口检查，
不运行 OpenFOAM，不计为物理成绩；未知请求不自动重发。
只有成功的接口记录与绑定源码的测试全部就绪才提交四题。

```bash
bash ci_checks/science.sh prepare --config experiments/science-kimi-code.yaml
bash ci_checks/science.sh check --config experiments/science-kimi-code.yaml
bash ci_checks/science.sh submit --config experiments/science-kimi-code.yaml --allow-paid --run-name kimi-code-k3-output
```

每次 submit 新建时间戳归档，包含配置、源码、接口证据、成绩和实时 transcript。
提交成功不等于题目通过；查看归档内的 `results/scoreboard.md`。
