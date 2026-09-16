# 题面规范：考察物理语言到求解器语言的转换

适用于所有自主网格题。物理条件必须明确，配置实现由 Agent 完成；不能靠故意漏条件制造难度。

## 各文件只承担一件事

|公开文件|应当包含|不应包含|
|---|---|---|
|instruction.md|物理问题、材料、初边值条件、物理模型、几何语义、目标时刻|字典键名、边界条件类名、配置代码、网格划分模板|
|geometry/|单位、坐标系、外形、材料界面、边界标签|体网格、网格单元编号、参考解|
|protocol.md|工具能力、运行与报告接口、支持格式、安全与预算限制|本题的配置答案|
|observations.md|观测位置、方向、单位、时间、统计定义、提交结构和精度要求|隐藏参考数值、由模型表现倒推的容差|

实际模型 prompt 完整拼接这三份公开 Markdown，并列出几何位置；不是只发 instruction.md，也不是让模型寻找不存在的协议。
专家预览和正式运行使用同一个 public_task.render，发现私有审阅文字就阻断，不静默过滤。

## 每题发布前逐项核对

1. 几何单位、坐标方向、二维/一维简化或三维实体壁面；多材料间的接触关系。
2. 材料参数、单位、状态方程、黏度/温度关系；物理模型的具体含义与必要系数。
3. 初始速度、温度、压力及其他实际输运量。分段初值应给位置、两侧数值和启动事件。
4. 每类入口、出口、壁面、周期面和材料界面。包括回流条件、热条件、压力是绝对/表压/运动学压力及其参考。
5. 重力、体积源、热源、外加压差；明确哪些物理作用忽略，避免模型合理猜测却被判错。
6. 瞬态终止时刻，或有证据支持的稳态目标；数值迭代次数不是物理时刻。
7. 报告的每项物理量都在 observations.md 有可执行定义。允许列数学公式，但不提供求解器编码。

例如写“上壁自 t=0 起以 1 m/s 向 x 正向运动，下壁静止，两壁无滑移”，而不写如何填写速度场边界字典。
写“入口给定总压、出口给定静压及回流条件”，但由模型选择相应的 OpenFOAM 实现。

不限制题面行数；完整性比刻意简短重要。通用文档可以查阅，但不能承担补齐本题缺失物理条件的职责。

## 作者侧的底线

2026-09-15 policy update: the expert may explicitly accept a finite-resolution numerical reference with recorded limitations. That acceptance is separate from an automated convergence certificate and is not blocked by a demand for further convergence studies. Keep exact source provenance, do not rewrite historical qualification results, and do not imply that accepting a reference automatically implements its scoring/release integration. The current s-20x decision and English statements are documented in [the English review](ENGLISH_20X_INSTRUCTION_REVIEW_20260915.md).

物理条件不清楚、参考解不合格、跨网格 grader 未验证时，在私有注册清单标为待审，阻断该版本启动。
不能把作者审阅提示放进 instruction.md；不能悄悄加载同题号旧版来填补新版缺口。
自动测试只能检查泄漏、组装、单位/字段和已编码约束，不能替代专家判断物理问题是否定义充分。
修改已发布物理设定、观测定义或 ground truth，必须建立新版本，保留旧成绩和证据。
