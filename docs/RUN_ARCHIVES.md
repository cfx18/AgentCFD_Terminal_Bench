# 每次启动一个带时间指纹的完整归档

正式入口 `ci_checks/science.sh submit` 现在自动创建新目录。不再把本轮配置、启动日志、结果分散在多个可变位置。旧记录不会迁移或覆盖。

目录名例子（仅示意）：`sol-20260915T123040123456Z-a81c93b94e22-61ba947f`。
组成是可选标签、UTC 微秒时间、实际配置 SHA256 前 12 位、8 位随机后缀。完整 SHA256 和创建时间写入 `run.json`。相同配置同时提交也不能覆盖；目录创建冲突直接失败。

## 布局

```text
runs/manual/<自动生成的运行ID>/
  run.json                    身份与归档意图，不代表已启动
  archive.json                snapshots 全部文件的哈希与封存时间
  snapshots/
    requested.yaml 或 .json   当次解析的原始配置，保留注释
    effective.json            当次解析后的有效配置
    preparation.json          YAML prepare 的绑定证据（旧 JSON 无此项）
    source-matrix.json        原始任务矩阵
    matrix.json               实际执行矩阵，验收依赖改指本归档的副本
    execution.json            实际路径、认证引用及外部依赖说明
    runtime/                  实际使用的冻结代码、逐题配置、题面、schema、私有参考/验收、文档
    controller/               当次使用的启动器副本
    probe/                    接口资格的 spec/result 原始凭据
    tests/                    当次就绪检查使用的 JUnit 报告
    references/               所选题已有参考运行的原始证据，未重新求解
    release-audit.*            发布审计报告（配置指向的文件存在时）
  readiness.json              副本就绪检查结果
  launch-request.json         启动命令意图，先于进程启动写入
  launcher.stdout.log         启动器标准输出与错误
  launcher-exit.json          观察到的启动器退出码，不是测试终态
  launch/
    controller.log            独立后台控制器日志
    intent.json / process.json
  results/
    campaign/                 矩阵、子进程身份、退出和完成凭据
    qualification/            本轮的独立验收资格记录
    trials/                   各题 DB、Agent 轨迹、请求响应、提交、原生输出和验收结果
      <task>/transcript.md     实时追加的中文 I/O 阅读版，不是结束后导出
      <task>/transcript.jsonl  同步追加的结构化 I/O
    scoreboard.md / .json      本轮成绩汇总
```

整个归档只在宿主侧，创建权限为 0700；不挂载到被测 Agent。标准认证文件、配置指定的 env 文件或登录目录不复制。

[实时 transcript](LIVE_TRANSCRIPTS.md) 在每次捕获提示词、回复、工具观察或验收反馈时直接追加，不是事后导出。
它不要求每条 I/O 保存哈希；本页的配置快照与既有审计凭据仍保留独立的完整性校验。
`requested.yaml` 保留原始内容，所以仍然禁止把密钥写进 YAML 的字段或注释。API key 只保存在宿主 env 文件中。

配置、题目、模型调用轨迹、提交文件和被执行器收集的结果均保留。宿主 Python 环境、harness 二进制、OpenFOAM 镜像与远端集群临时工作目录不打包；它们的版本/身份仍由原有配置与执行凭据记录。因此这是可审计的实验归档，不是无需外部依赖即可运行的整机镜像。

## 命令

以下从原项目根目录执行。先按现有流程 prepare/check；发布阻断仍有效，新增归档功能不会绕过它们。

```bash
bash AgentCFD_Terminal_Bench/ci_checks/science.sh submit --allow-paid

# 可选：增加一个短标签；完整目录名仍自动生成。
bash AgentCFD_Terminal_Bench/ci_checks/science.sh submit --run-name sol --allow-paid
```

每个 submit 都表示**新的、明确授权的实验**。不要为了恢复未知请求而重复 submit；同一配置会得到新目录，但不是原实验的恢复。

启动时会打印绝对 Archive 路径。复制该路径查看结果，即使原 YAML 后来改名或删除也可以：

```bash
bash AgentCFD_Terminal_Bench/ci_checks/science.sh status --run-dir /absolute/path/to/archive
tail -F /absolute/path/to/archive/launch/controller.log
```

也可用 `status --run-name <完整运行ID>` 按当前 YAML 的 `output_parent` 查找；旧的固定目录与旁边的 `-launch` 目录仍能读取。新版的 `--run-name` 在 submit 中是标签，在 status 中是完整 ID，不用标签猜测“最新一次”。

## 失败、中断与恢复

1. 未通过最初的就绪门禁：不注册测试，不创建一份伪装成运行结果的目录，不发模型请求。
2. 快照失败：保留 `run.json`、部分副本和 `archive-error.json`；没有封存凭据就不启动。
3. 副本检查失败：保留 `readiness.json`，不启动。原代码和副本之间的差异不能被忽略。
4. 启动器返回错误：先保存真实退出码，再显示日志；所有材料留在同一归档，不自动重试。
5. 启动过程被中断、结果未知：保留 `launch-request.json` 和 `launcher-interrupted.json`，不伪造退出码。应先检查原子进程/作业凭据。
6. 后台运行结束：以 `results/campaign/finished.json` 和各题结果为准；`launcher-exit.json` 返回 0 只说明启动器返回成功。

未来或底层显式恢复应继续使用同一个归档中的 `results/` 和冻结快照。此次没有新增一键 resume，不能据此绕过已有的未知请求恢复审计。

源码入口：[run_archive.py](../ci_checks/run_archive.py)、[submit_science.py](../ci_checks/submit_science.py)；
无付费调用的测试：[test_run_archive.py](../ci_checks/test_run_archive.py)。
