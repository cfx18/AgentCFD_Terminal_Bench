# 一份 YAML，自己提交与查看，不需要 Agent 监控

主要编辑 [experiments/science.yaml](../experiments/science.yaml)。注释列出了 harness、模型、十道登记题、文档条件及预算。入口需要 Python 3.12 和 PyYAML 6；当前机器的 `/usr/bin/python3` 已有 PyYAML，项目依赖也已声明。

## 现在的完成边界

- YAML 编译、旧 JSON 兼容、四种 harness 参数传递已实现，经过无付费调用的测试。
- **不代表新的真实接口测试已通过。**改变桥接代码、客户端或模型，需要重新取得相应证据。
- 默认选择 `geometry-only-free-mesh-draft-v1`：十题统一只给几何初始文件和物理题面，由模型自行划分网格；跨网格验收尚未发布，compile/prepare/submit 均拒绝，绝不回退到固定网格任务。
- 当前模型为 Sol xhigh，显式禁用子 Agent。真实 CLI／本地假 API 已验证文件操作、文档、隔离与恢复；这不是在线模型或额度可用性证明。
- 传输事故与恢复修复的过程、回归证据及剩余阻断见 [收尾记录](PIPELINE_COMPLETION_20260915.md)。默认 `release.ready: false`，未启动付费模型评测或新集群任务。

新题面、几何与逐题验收问题见 [自由网格审阅说明](../task-drafts/geometry-only-free-mesh-v1/README.md)。上一版 `physics-intent-v1` 草案保留为历史。
`registered-v1` 只表示旧的固定网格任务，不能当成新的几何输入评测；本轮不启动它。
新增 `geometry-only-free-mesh-v1` 为明确的另一版本：s-001 已打通原生执行与跨网格验收，
其余九题保留待审。可离线准备[单题工程配置](../experiments/free-mesh-s001-review.yaml)，
但该配置仍不允许付费启动。不能把主实验里的未完成任务自动删掉来运行此配置。

## 常改的配置

|设置|实际作用|
|---|---|
|`name`|不可覆盖的准备快照名称；改配置后用新名称|
|`harness.name`|codex / foamclaw / claude-code / kimi-code，实际传入现有 factory|
|`harness.backend`|订阅或自定义 API，认证方式不混用|
|`model.name`|明确的模型 ID；不会按昵称猜测、自动换模型或降级|
|`tasks`|题号列表，顺序就是执行顺序；支持所有十道已登记题|
|`budget.model_calls`|每题累计调用次数；无额外输出 token、总 token、费用上限|
|`budget.native_seconds / per_run_seconds`|OpenFOAM 总执行／单次执行安全时限|
|`budget.request_seconds`|单次请求故障看门狗，不是单次输出 token 限制|
|`documentation`|固定 OpenFOAM 通用文档库，或 none；不支持任意联网模式|
|`execution`|Python、快照与输出目录；当前控制器只支持串行，非 1 并发会报错|
|`evidence / release`|对应版本的接口测试、回归证据与人工发布门禁|

所有相对路径相对于 `AgentCFD_Terminal_Bench`，不依赖命令执行目录。密钥只在宿主 env／登录目录中，不写入 YAML。模型注释是本项目明确支持的 ID，不是提供商的实时可用模型目录。

## 四个命令

从原项目根目录执行，或使用脚本的绝对路径：

```bash
cd /root/shared-nvme/Caifeixue/AgentCFD

# 离线生成快照和每题 JSON。默认物理草案会拒绝，不会自动改用旧题。
bash AgentCFD_Terminal_Bench/ci_checks/science.sh prepare

# 只检查配置/快照/证据，列出阻断项；不会查账户或使用模型额度。
bash AgentCFD_Terminal_Bench/ci_checks/science.sh check

# 仅在对应版本已修复、验证、人工放行后执行。运行目录自动带时间指纹。
bash AgentCFD_Terminal_Bench/ci_checks/science.sh submit --allow-paid

# 用启动时打印的绝对 Archive 路径查看，不依赖后来修改的 YAML。
bash AgentCFD_Terminal_Bench/ci_checks/science.sh status --run-dir /absolute/path/to/printed-archive
```

每个命令都可加 `--config experiments/my-campaign.yaml`。旧 `manual-science-launch-v1` JSON 仍可用于 check/submit/status，但不使用 prepare；历史示例为 `experiments/sol-ultra-five-manual-v1.json`。

prepare 只生成源码快照、实验 JSON 和绑定原始 YAML 内容的清单。它不安装 harness、不读密钥、不运行接口烟测、不做 OpenFOAM 资格检查；**prepare 成功不等于付费就绪**。改变 YAML 后，check 会要求新快照，不会无声修改已准备或已开始的实验。

发布完成后，submit 使用原有 detached controller。关闭终端或这段对话不影响它运行；后台记录日志和表格不调用 LLM，只有模型作答使用额度。

每次 submit 在 `output_parent` 下自动生成独立目录，名称为 UTC 微秒时间、配置 SHA256 前 12 位和随机后缀。
可加 `--run-name sol` 作为不超过 32 字符的标签，但它不再代表完整目录名。
启动时会打印准确的 Run ID、Archive、Log 和 Table 路径，不需要人工拼接。

完整布局、失败语义及查看方式见 [单次运行归档](RUN_ARCHIVES.md)。成绩位于归档的 `results/scoreboard.md` / `.json`，
后台日志位于 `launch/controller.log`。status 显示表格更新时间与完成凭据，但旧表不是进程存活证明；不对未知请求盲目重试。

## 切换到自定义 API

修改 YAML 的相关段落（其他段落仍保留）：

```yaml
harness:
  name: codex
  backend: custom-api
  reasoning_effort: null
  public_decision_log: false
model:
  name: AWS-Claude-Fable-5
authentication:
  env_file: /absolute/path/private-science.env
```

env 中使用 `SCIENCE_API_BASE` / `SCIENCE_API_KEY`，兼容 `OPENAI_BASE_URL` / `OPENAI_API_KEY`。当前自定义 API 的公开决策日志开关尚未适配，不会假称已开启。FoamClaw / Claude Code / Kimi Code 目前只允许 `custom-api + Kimi-K3`；其他组合须扩展并验证桥接后再加入。各客户端仍须提前安装在宿主，快照不会带入用户登录信息；客户端文件哈希绑定接口证据。

## 代码结构

```text
experiments/science.yaml       用户选择
ci_checks/campaign_config.py   严格解析、能力检查、生成现有格式
ci_checks/submit_science.py    prepare / check / submit / status
ci_checks/run_archive.py       自动时间指纹目录、配置/代码/证据副本与完整性检查
ci_checks/freeze_science_runtime.py
                              独立源码快照，连同生成配置一起哈希
ci_checks/launch_science_matrix.py
                              启动脱离终端的控制器
ci_checks/run_science_matrix.py
                              顺序调度、原生资格、退出凭据、成绩表
ci_checks/matrix_lifecycle.py  回收绑定的子控制器退出证据、基础设施错误暂停
ci_checks/release_evidence.py 测试报告绑定实际源码和必测项目
ci_checks/release_pytest.py   执行测试时生成绑定，不能给旧 XML 后补通过凭据
ci_checks/run_codex_science.py 历史文件名；现在参数化选择四种已有 harness
agentcfd_bench/smoke/agent.py  已有隔离 factory 与真实客户端
```

没有加入新的 Agent 推理循环，也没有自动切换 API、自动补算或批量重试 error。配置仅在已支持范围内生效，能力不足会在启动前阻断。

## 测试证据与恢复边界

新的 XML 必须在测试开始时启用 `-p release_pytest --release-root <冻结运行目录>` 并指定新的 `--junitxml` 路径。
报告旁自动生成 `.binding.json`；测试前后源码必须一致，并覆盖事故必测项。xhigh 订阅额外要求真实 CLI＋本地假 API 测试通过；自定义 API 不强制订阅测试，但仍需它自己的原有真实接口 probe。
历史 XML 不补签，不同源码版本的报告不能拼成“通过”。归档同时复制 XML 和绑定记录。

矩阵恢复优先回收原启动的父/子控制器退出凭据；会核对 launch ID、任务、实验、协议及 PID 的启动时间/系统启动 ID。
原进程仍活着就继续观察，证据不足会阻断；不会重跑 qualification 或重发未知 API 请求。
401/402/403/429，或连续两题基础设施异常，触发 `campaign/circuit-*.json` 并暂停后续派发；模型物理答案错误不触发这个暂停。
修复原因后使用原冻结矩阵命令 `--resume --acknowledge-circuit --allow-paid` 才会明确确认继续剩余题；这不重跑失败题，也不清除历史记录。
真实配额恢复时间没有证据时记录为 unknown，不猜测。前端 `submit` 始终新建实验，不是 resume。
