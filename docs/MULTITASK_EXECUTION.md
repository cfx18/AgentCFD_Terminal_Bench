# 多任务执行边界（从零建模）

本轮只完成通用执行边界；不会把测试夹具当成已批准的 tutorial 题目。
新五题仍必须分别完成题面、物理验收、原版运行与正负对照后才可上线。

## 一道题贯穿整个会话

```text
experiment.task → 注册表 + 内容哈希 → TaskPackage
                                      ├─ instruction.md → Agent（无参考文件）
                                      ├─ execution → NativeService → 冻结结果
                                      ├─ acceptance → 报告验收
                                      └─ reference → 私有资格正负对照
```

- `task_package.py:TaskPackage` 绑定任务 ID、版本、运行环境、文件摘要与配置摘要。
- `execution_spec.py:ExecutionSpec` 读取任务自己的命令、完成条件、输出字段和资格运行预算。
- `engine.py:run/resume` 选择本题 prompt / action parser / evaluator，并核对验收环境题目。
- 会话持久化整个执行代码摘要；旧会话未记录摘要或代码发生变化时拒绝恢复，旧报告仍可读取。
- `runtime.py:NativeService` 保存本题和输入摘要；只执行固定命令，不从模型 action 取 shell。
- `qualification.py:qualify/require_qualified` 对本题参考和反例验收；其他题的资格证据不能复用。
- 命令行 `prepare --qualify-native`、`run`、`resume` 均显式传入选定任务。

原有 `s-001/couette-transient-2` 的题包和注册摘要不变。它缺少的旧执行元数据仅由
精确 ID/版本的兼容分支补全；新题缺元数据直接报错，不继承“2 秒 / U,p / 顶壁”。
`spec.RUNTIME/METRICS`、`verify`、`fixture` 和 `runtime.COMMANDS` 仍为历史
校准/复核接口，不是新任务分派入口。

## 新任务的执行元数据

下面是接口示意，不是已批准实验，也不代表该题物理条件已经定义：

```toml
[metadata]
native_commands = [["mesh", "blockMesh"], ["mesh_check", "checkMesh"], ["solver", "pimpleFoam"]]
artifact_fields = ["U", "p", "k", "epsilon", "nut", "s"]
qualification_seconds = 120

[metadata.acceptance_groups]
report = ["report_matches_artifacts"]
physical = ["task_contract", "physical_quantities"]

[metadata.native_completion]
kind = "transient"
end = 1.5
tolerance = 1e-8
early_convergence = false
```

执行顺序为 mesh → mesh_check → solver → 可选受审后处理。当前只登记首批需要的
三个求解器及标准命令；添加任意其他命令或命令参数必须修改安全列表并加测试。
允许配置 `pimpleFoam` 不代表已允许任意 function object：输入安全策略仍由本题
`safety_inputs` 审阅，标准库和标量源项支持尚待逐题完成。

瞬态终点用秒；稳态终点用迭代索引。仅稳态可显式允许提前收敛，并要求
v2306 `simpleControl::loop` 的原生 `SIMPLE solution converged in ... iterations`
证据与最后一个 `Time =` 值一致。退出成功、存在 End 或一句“converged”均不够。
完成条件不是物理正确性结论。

输出只允许任务登记字段和执行阶段日志；零时刻输入、目录越界、参考路径以及
另一题专属字段不会被发布。字段文本仍须由本题 extractor 验证维度、大小、终点与数值。

新题必须声明报告真实性检查与物理检查的分组。分组随每次评价事件持久化；报表
只读取该次事件，不去加载今天的题包猜昨天的检查名，也不再写死 Couette 的指标。

## 私有资格接口

`solution/reference.py` 提供：

- `reference_files()`：完整原版输入，不作为 Agent 起始文件。
- `qualification_controls()`：返回 `valid / invalid / wrong_physics / invalid_stage`。
  valid 必须与 reference_files 一致，三个输入必须不同；invalid 必须明确预期失败阶段。
- `fabricate_measurements(measurements)`：构造仍符合本题报告结构的伪造数值反例。

`tests/acceptance.py` 提供 `safety_inputs / physics_contract / parse_action / extract / evaluate`。
没有解析解的题不再被强制要求放置一个空的 `tests/analytic.py`。

资格检查要求四项同时成立：正确参考通过；非法输入失败；物理错误反例能够运行但
验收失败；伪造后处理失败。原版参考运行失败会保存未通过的资格结果，不因输出缺失
抛出一个无上下文的提取异常，更不补判成功。

已保存的 control 直接读取并校验，不再调用 service.execute；运行中断仍交给
NativeService 观察同一个操作。读取资格时重放全部检查，不仅相信 passed 布尔值。
旧资格证据不覆盖，代码变化后需新建资格证据目录。

## 验证范围

`tests/test_task_dispatch.py` 临时建立两道**合成接口测试题**，使用不同题面、字段、
报告结构、求解器、终点以及三/四阶段工作流，验证：

- 从空输入开始、真实提交协议下的假模型/假执行器端到端通过。
- 0.3 / 0.5 / 1.5 终点不再被统一判作 2；稳态提前收敛必须有特定证据。
- 题目/服务不匹配时，在建运行目录和模型请求前拒绝。
- 不同题的字段、资格证据不混用；额外执行阶段受命令校验。
- 运行退出证据已保存、SQLite 尚未提交时恢复，不重复启动求解命令。
- 参考运行失败可记录；完成的资格控制不重复执行。
- 旧/不同执行代码禁止恢复，内存配置变化在原生调用前拒绝；报表沿用冻结分组。
- 已完成资格控制文件缺失时拒绝准入，不能调用执行器重新填补证据。

这些测试证明通用接口和恢复行为，不证明五个真实 tutorial 的物理验收已通过。
