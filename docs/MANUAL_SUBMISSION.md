# 命令行提交：旧 JSON 入口说明

日常使用请看新版 [YAML 配置与四个命令](YAML_CAMPAIGNS.md)，默认配置已改为 `experiments/science.yaml`。
下文保留旧 JSON 协议的说明。使用本页旧配置时，每条命令须加
`--config experiments/sol-ultra-five-manual-v1.json`；旧 JSON 不使用 prepare。

配置文件：[sol-ultra-five-manual-v1.json](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/experiments/sol-ultra-five-manual-v1.json)。

入口：[science.sh](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/ci_checks/science.sh) → [submit_science.py](/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/ci_checks/submit_science.py) → 已有 detached launcher → 冻结版本的 matrix → 各题控制器。

普通后台进程负责模型调用、原生执行、写日志和成绩表；不需要打开这段对话，不需要 Agent 定时查询。文件监控本身没有 LLM 调用，作答仍会消耗订阅／API 额度。

## 当前是否可以启动

**暂时不可以。**9 月 15 日审计发现当前冻结版本仍有传输与状态缺陷，因此配置里的 `release.ready=false`。`check` 会列出阻断项并退出 2；`submit` 也会在创建作业之前拒绝。不是让你再次尝试消耗额度。

修复并验证后，需要更新配置中的 `runtime`、`probe`、`junit`，完成审阅后才能设置 `release.ready=true`、清空 `blockers`。这些字段是明确的人工发布门禁，不是 bug 自动修复器。旧版 XML 通过不等于新版本已验证；旧版接口烟测也不能复用于改变后的桥接代码。

## 1. 检查配置——不收费

以下从旧项目根目录运行；也可用脚本的绝对路径，从任意目录运行。

```bash
cd /root/shared-nvme/Caifeixue/AgentCFD
bash AgentCFD_Terminal_Bench/ci_checks/science.sh check
```

检查模型、ultra、每题 64 次总调用、五题清单、冻结版本、原始接口烟测校验和、桥接源码哈希、测试报告。不会读取密钥内容、查询账户、发模型请求或申请 OpenFOAM 作业。`ready=true` 仅表示静态前置检查通过；实际 launcher 仍会检查运行环境，各题仍需原生资格检查。

## 2. 提交后台任务——明确允许使用额度

**仅在修复／验证并解除发布阻断后使用。**运行名必须是新的；已存在的任务目录不能再次提交。

```bash
bash AgentCFD_Terminal_Bench/ci_checks/science.sh submit \
  --run-name sol-five-003 \
  --allow-paid
```

提交成功会打印 PID、日志和成绩表路径。启动器脱离终端运行，关闭终端不会要求 Agent 接管。默认五题串行，保持既有每题 64 次累计模型请求；不增加单次输出 token 上限。仅查固定 OpenFOAM 文档库；参考与 verifier 不进入 Agent 工作区。

## 3. 查看进度——不收费、不触发恢复

```bash
bash AgentCFD_Terminal_Bench/ci_checks/science.sh status --run-name sol-five-003
```

该命令仅显示成绩表、更新时间、控制器完成凭据是否存在。**它不是进程存活证明**；控制器故障后旧表可能过时，需结合日志与退出凭据。它不会悄悄重发失败请求。

持续看日志：

```bash
tail -F /root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/runs/manual/sol-five-003-launch/controller.log
```

看表：

```bash
cat /root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/runs/manual/sol-five-003/scoreboard.md
```

上述日志／表路径由 `output_parent` 和运行名决定。按 Ctrl-C 退出 `tail` 只停止看日志，不停止任务。

## 改哪些配置

所有相对路径均相对于 `AgentCFD_Terminal_Bench`，不依赖当前终端目录。

|字段|作用|
|---|---|
|`python`|执行环境；保留 `.venv-harbor/bin/python` 的路径，不解析到系统解释器|
|`runtime`|经过验证的冻结代码目录，不直接运行持续修改中的工作树|
|`manifest`|五题顺序及每题实验配置文件名|
|`model` / `reasoning_effort`|本轮明确为 `gpt-5.6-sol` / `ultra`，与每题及 probe 必须一致|
|`model_calls_per_task`|校验值，当前为 64；要改预算必须创建相应的新实验配置，不能只改这里|
|`authentication`|宿主认证路径；不要将密钥写进这个 JSON|
|`probe` / `junit`|对应冻结版本的接口与测试证据|
|`output_parent`|输出父目录，默认 `runs/manual`|
|`release`|人工审阅的发布状态与阻断原因；不能靠清空原因跳过修复|

使用另一份配置：

```bash
bash AgentCFD_Terminal_Bench/ci_checks/science.sh check --config experiments/my-manual.json
bash AgentCFD_Terminal_Bench/ci_checks/science.sh submit \
  --config experiments/my-manual.json --run-name my-run-001 --allow-paid
```

## 保留自定义 API

入口支持两个后端，但不能混在同一次运行中。自定义 API 配置的认证部分为：

```json
{
  "authentication": {
    "backend": "custom-api",
    "env_file": "/absolute/path/to/private-science.env"
  },
  "reasoning_effort": null
}
```

这只是需要替换的字段示例，不是完整配置。必须同时选择该模型的 manifest、冻结实验与已通过的接口 probe。旧自定义 API 路径读取 `SCIENCE_API_BASE` / `SCIENCE_API_KEY`，兼容 `OPENAI_BASE_URL` / `OPENAI_API_KEY`；本次没有改写任何现有 env 或登录文件。

## 失败与恢复

本入口故意没有“一键重试所有 error”。当前矩阵恢复还有审计中的缺口；不提供一个可能重复收费的假安全 resume。先看原请求是否已经完成、子控制器退出凭据是否完整，再做显式回收。不要通过换运行名把同一未知请求伪装成免费首次尝试。

当前任务的正式记录仍在 `runs/sol-ultra-five-002`，没有搬迁或覆盖；新入口写入 `runs/manual`。
