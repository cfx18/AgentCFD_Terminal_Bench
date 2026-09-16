# Fable 五题｜专家审阅入口

先看三件事：

1. **自然对流不是“完全不会改”。** 首次报告不通过后，Agent 已提出改用 limitedLinear 0.2，随后被接口截断，修改没有执行。应审阅这个诊断是否合理，不能写成“没有诊断能力”。
2. **温黏度题不是“未理解温度依赖”。** 返回片段已区分“Bird–Carreau 退化成常数”与“Arrhenius 温度因子仍保留”。真正悬而未决的是能量方程／粘性耗散如何配置；检索也没有提供关键文档。
3. **当前没有五题最终通过率。** 两题通过，三题接口中断；只有自然对流留下了一份可审阅的数值验收失败报告。

每题按“看到了什么 → 思考摘要 → 决策 → 实际 action → 结果 → 归因待审”展开。
先读粗体结论和优先步骤，需要核实时再打开证据；不需要先读源码。
检索卡另列实际关键词、返回内容、Agent 是否明确采纳，以及影响了哪个下一步。


| 题目 | 当前结论 | 优先看哪一步 |
|---|---|---|
| [三维封闭腔自然对流](</root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/expert_reviews/fable-five-20260914-v1/s-204.md>) | 一次报告验收失败；后续被 API 截断，题级结论未完成。 | C04 数值选择 → C06 修复 → C10 验收 → C11/C12 未执行的诊断。 |
| [温度依赖黏度与能量输运](</root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/expert_reviews/fable-five-20260914-v1/s-203.md>) | API 中断；没有生成可提交配置，不能给物理答案打分。 | C03/C04 物理识别；Q01–Q07 检索质量；C05–C07 未验证实现。 |
| [多区域传热与接触热阻](</root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/expert_reviews/fable-five-20260914-v1/s-202.md>) | API 中断；只做目录探测，没有原生提交。 | C02–C04：计划很长但没有落地；不要把计划当成已做动作。 |
| [压力驱动分支流与标量源项](</root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/expert_reviews/fable-five-20260914-v1/s-105.md>) | 通过；一次网格配置错误，经原生反馈自行修复。 | C02/C03 初始边界处理 → C07 最小修复；C05 版本语法自查。 |
| [可压缩激波管](</root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/expert_reviews/fable-five-20260914-v1/s-205.md>) | 一次原生提交、一次报告即通过。 | C03 初始状态／状态方程；C04 数值选择；C08 物理解读的证据边界。 |

## 怎么给意见

直接回复“s-204-C11：我认为……；应当……；是否可用于训练……”即可定位。
也可用表格软件填写 [专家意见.csv](</root/shared-nvme/Caifeixue/AgentCFD/AgentCFD_Terminal_Bench/docs/expert_reviews/fable-five-20260914-v1/专家意见.csv>)，一行对应一步／一次检索。
主因建议：物理理解／数值方法／配置语法／检索策略／资料缺口／接口／管线／基准定义／无错／证据不足。
原始评分不随意见自动改变；专家确认、标准答案核实和数据版本登记后，才决定是否入训练集。

## 完整性与边界

覆盖 42 次模型请求、7 次检索、全部 5 次原生提交。
每步都有原始凭据路径与 SHA256；中文解释是报告作者的草稿，不是 Agent 逐字原话或专家结论。
上游返回的 thinking 只是可见片段，可能不完整；计划写文件不等于工具执行，更不等于已经提交求解。
本次只重组历史记录，没有请求模型、重跑 OpenFOAM、改旧提示词、改评分或自动制造训练标签。
