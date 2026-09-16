# 五题 × 四 Harness：独立运行与监控

**最新状态：**002 全部终止，[终局审阅表](SCIENCE_MATRIX_002_FINAL_REVIEW.md)。
build-006 已在终局后合入；[正式部署验证](SCIENCE_RELEASE_006.md)。以下维护段落是历史。

这条入口只运行从零建模，不调用旧混合烟测或改错题。统一 Kimi-K3、断网、
固定只读 OpenFOAM 文档；四种真实客户端为 Codex、FoamClaw controlled、
Claude Code、Kimi Code。它衡量受控工具条件下的 harness 表现，不是默认产品排名。

2026-09-13 维护状态：001 因已确认的验收/提交缺陷中断，源码和记录归档。
修复已部署，536 项完整回归通过，五题原生资格全部通过。
用户已确认开始重测，002 已启动独立付费控制器；不要再次 launch 活动批次。
启动与逐题审阅见[002 观察记录](SCIENCE_MATRIX_002_OBSERVATIONS.md)。
具体影响与证据见[修复审阅说明](VERIFIER_BOUNDARY_FIX.md)。

上述“已部署修复”只指 001→002 的末轮提交和 AMI 修复。002 运行中又发现
v2306 静态兼容及显式默认系数误拒、目录/提交协议歧义、文档查询排队、
上游终态误分类以及失败锁止后的本地退避问题；
[新候选组合 build-006](../review_candidates/integrated_release_v1/README.md)已通过 758 项回归，
仍未部署、未取得新原生资格。002 的原始失败与候选复核必须分列，不能把当前
成绩宣称为无验收器缺陷的最终排行榜，也不能用候选身份恢复旧会话。
默认系数的三个额外单变量原生控制已登记、尚未执行；生成器的 7 项检查另计，
不是原生资格或更大规模完整回归。现有标准五题资格也须在最终源码上重新取得。

## 正式职责与代码

~~~text
experiments/tutorial-science-first-batch-v1.json
            │ 固定任务/模型/文档/预算
science_campaign.prepare → 冻结选择 + campaign.sqlite 中全部 20 个试验
            │
qualification.qualify → 导入原版正例 + 真实运行三个控制
            │                 └ 缺 U / 错误物理 / 更严格线性容差
tutorial_packages.publish → 五题全部门禁通过才发布，保留旧 s-001
            │
science_campaign.launch → 脱离调用进程的独立控制器
            │
engine.run/resume → 四种实际 harness → 独立 OpenFOAM → 后处理与定量验收
            │
science_campaign.report → 只读状态/凭据 → scoreboard.md/json
~~~

- [批次 prepare / execute / launch / report](../agentcfd_bench/science_campaign.py)。
- [原版正例导入和六项门禁](../agentcfd_bench/qualification.py)。
- [旧执行身份重建](../agentcfd_bench/reference_prepare.py)：ImportedReferenceTask。
- [全批次发布](../agentcfd_bench/tutorial_packages.py)：publish；不覆盖已有题包。
- [逐题执行与恢复](../agentcfd_bench/engine.py)。
- [四个真实客户端与匿名环境](../agentcfd_bench/smoke/agent.py)：只复用客户端，
  不调用同目录下的旧 campaign.py 或 repair 验收。

## 当前路径

本地项目根目录：
/root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench

本机控制器使用已有专用 Python：
/root/shared-nvme/Caifeixue/AgentCFD/.venv-harbor/bin/python

默认 /usr/bin/python3 没有安装 dotenv/Harbor，不能直接替换。批次记录解释器及
httpx、python-dotenv、Harbor 版本；恢复时验证一致性。无需为此修改全局环境。

- 实验配置：experiments/tutorial-science-first-batch-v1.json。
- 当前已发布题包的暂存源：data/tutorial-science-packages-v2/；正式注册在 tasks/dataset.toml。
  v1 保留，不覆盖。
- 修复后批次：runs/tutorial-science-matrix-002/（已授权并启动）。
- 修复后原生门禁：runs/tutorial-science-qualification-002/。
- 旧批次和门禁 001 均保留，不用修复版在旧身份上续跑。
- 只读复用的原版：runs/tutorial-reference-preparation-001/。
- API 配置仍读取用户已配置的父项目 .env；只供宿主 broker 使用，不挂载给 agent。
  支持 SCIENCE_API_BASE/SCIENCE_API_KEY，或既有 OPENAI_BASE_URL/OPENAI_API_KEY。

## 可重复调用的命令

以下命令在项目根执行，用上面的专用解释器替换 PYTHON。prepare 的新目录不可
覆盖（002 已经准备，无需重复 prepare）；其余命令读取已有版本和证据，不重新选题或换模型。

~~~bash
PYTHON -B -m agentcfd_bench.science_campaign prepare \
  --root runs/tutorial-science-matrix-002 \
  --experiment experiments/tutorial-science-first-batch-v1.json \
  --staging data/tutorial-science-packages-v2 \
  --legacy /root/shared-nvme/Caifeixue/AgentCFD

PYTHON -B -m agentcfd_bench.science_campaign qualify \
  --root runs/tutorial-science-matrix-002 \
  --qualification runs/tutorial-science-qualification-002 \
  --originals runs/tutorial-reference-preparation-001 --execute-native

PYTHON -B -m agentcfd_bench.science_campaign publish \
  --root runs/tutorial-science-matrix-002 \
  --qualification runs/tutorial-science-qualification-002

PYTHON -B -m agentcfd_bench.science_campaign launch \
  --root runs/tutorial-science-matrix-002 \
  --qualification runs/tutorial-science-qualification-002 \
  --env-file /root/shared-nvme/Caifeixue/AgentCFD/.env --allow-paid

PYTHON -B -m agentcfd_bench.science_campaign status \
  --root runs/tutorial-science-matrix-002
PYTHON -B -m agentcfd_bench.science_campaign report \
  --root runs/tutorial-science-matrix-002
~~~

launch 使用独立进程会话、关闭输入继承、重定向日志；不是需要主 agent 持续
执行下一步才能推进的任务。它记录 PID、启动时钟和系统启动 ID，防止把复用 PID
误认成原控制器。活动控制器不重复启动；退出后再次 launch 恢复原批次。

~~~bash
tail -F /root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/runs/tutorial-science-matrix-002/controller.log
~~~

直接阅读：
[新批次实时表](../runs/tutorial-science-matrix-002/scoreboard.md)、
[旧批次保留表](../runs/tutorial-science-matrix-001/scoreboard.md)。
[逐题付费审阅记录](SCIENCE_PAID_OBSERVATIONS.md)保留实际错误、修改和数值结果。
控制器每 5 秒读取状态；只有变化时在日志输出 progress，避免刷屏。
API 调用中的进展取自宿主 dispatch/complete/error 凭据，不能把未返回时的调用
误显示成“没有调用”。逐题 token、费用、文档、运行和验收记录保留在 trials/ 下。
历史文档 response.json 的 HTTP 200 只证明宿主生成响应，不证明客户端收到了文本。
002 已有客户端查询超时的实证；旧 returned_characters 应按生成字符解读，
缺少传输凭据的记录不能补造已送达。独立文档服务与新统计仍属未部署候选。

## 门禁与恢复语义

每题六项：

1. 原版已完成输出被新验收接受，保留原执行身份和原始结果哈希。
2. 缺 U 输入被 OpenFOAM 原生启动拒绝。
3. 错误物理输入可以完整运行，但验收拒绝。
4. 篡改报告被拒绝。
5. 更严格线性容差的合理数值变化仍被接受。
6. 错误物理的整场比较也失败，不能只靠配置检查证明验收有效。

原版导入需要退出、日志、输入、运行环境、输出、资源释放等完整凭据；
不会把旧结果 task 字段改成新身份。对照执行已有退出就回收日志，不重跑。
资格结果已经保存但控制文件丢失时拒绝使用，不临时补跑伪装成原证据。

逐题模型调用未知时不自动重发，记录基础设施中断并继续其他注册试验。
原生阶段状态未确定时，只在固定观察窗口内 resume 同一个操作；
不重置模型调用预算。取消控制器时保存现有阶段，下次观察原题而非重新答题。
已知异常和模型答案失败分开统计，分母始终保留 20 个已登记试验。

每题保留 64 次累计模型 API 调用，无额外单次输出 token 上限；
600 秒累计原生执行、120 秒每次运行、600 秒单次 API 超时。上述原生/网络限制
是执行安全约束，token/费用/模型耗时另外统计；并发为 1。

## 验证证据

最初发布前完整测试：512 passed，0 failed，0 skipped，330.55 秒；
原始 JUnit：docs/tutorial-release-full-tests-20260913.xml。
修复后的主项目完整测试：536 passed，0 failed，0 skipped，371.30 秒；
原始 JUnit：docs/verifier-boundary-production-full-tests-20260913.xml。
首版五题真实原生资格均通过，见
[六项门禁及误差表](../runs/tutorial-science-qualification-001/report.md)。
修复版五题原生资格也全部通过，见[新六项门禁及误差表](../runs/tutorial-science-qualification-002/report.md)。

- [20 个真实客户端 × 新题接口测试](../tests/test_tutorial_harness_integration.py)：
  五题×四客户端从空目录构建、提交、文档访问、只读输出和后处理，已全部通过；
  API 与原生端为本地假服务，不是模型分数。
- [独立调度与恢复](../tests/test_science_campaign.py)：完整分母、普通失败、
  未知 API、原生 Pending、控制器中断、结果/事务提交间隙、重复调用和显式付费门禁。
- [导入与发布](../tests/test_tutorial_qualification.py)：旧身份保留、只新跑三个控制、
  缺凭据拒绝、保存结果不重发、全部门禁通过前不发布、保留旧题注册。
- 原生资格和最终付费运行证据分别保存在上面的独立目录，不能用这些假服务测试替代。
