# 当前范围：只推进 s-20x 物理题

> Superseding expert decision: all four existing numerical cases are accepted as Ground Truth. Their complete English public statements are in [the new review](ENGLISH_20X_INSTRUCTION_REVIEW_20260915.md). The numerical findings below remain historical evidence, not a requirement to reopen convergence studies or reject the expert's accepted references. No new model score is implied.

更新：s-202 的单相、无相变假设已获用户确认并写入题面，见[确认记录](S202_PHYSICS_APPROVAL_20260915.md)。
收敛判断不明确时先向专家提供压力、速度、温度场，见[场图审阅约定](EXPERT_FIELD_REVIEW.md)。
当前 s-204 场图见[5950/6000 次迭代对比](../audits/s204-field-review-20260915-001/README.md)。

用户明确：**s-10x 是故意做错的 case，本轮不用管，重点是 s-20x。**
此前将 s-10x 统一作为待修复物理参考推进，范围判断不正确。
不再对其继续数值修复、推进发布或将其缺口混入 s-20x 的就绪统计。
这不改变既有日志和作者调试事实，也不把过去所有运行失败都事后解释成故意设计。

## 四题此前的自动数值验证记录（专家接受前）

当前清单登记的是 s-202、s-203、s-204、s-205，未登记 s-201。
以下是作者验证，不是模型分数；本次范围调整没有启动模型或 OpenFOAM。

| 题目 | 已有证据 | 当前缺口 | 结论 |
|---|---|---|---|
| s-202 多区域接触热阻 | 新粗网格界面最大不平衡 1.37e-7，全局能量不平衡 0.2582%，123.44 秒完成 | 新耦合方案的跨网格、短时间窗口、完整正反控；局部约 483 K 的“水”是否明确按单相无相变理想化处理 | 待审，不能把粗网格修好当成全题合格 |
| s-203 温度依赖黏度 | 真实耗散反例有效；短窗口能量不平衡 0.1765% | 最细两级 p/k/ε 差 10.07%/10.26%/15.06%；最细运行 495.90 秒，超过模型单次 300 秒预算 | 参考精度未合格 |
| s-204 密闭腔自然对流 | 四次数值方案均回收；最后方案热不平衡 2.14% | 相邻输出速度变化 12.52%，未证明稳态；不能单凭迭代振荡断言物理必然非稳态 | 稳态参考未合格 |
| s-205 激波管 | 三网格、独立 Riemann 波形与守恒、错误右压、缺 U、假报告测试通过 | 候选尚非默认正式发布入口；正式模型运行仍需对应快照与接口就绪检查 | 当前代码下作者资格通过 |

因此当时的自动验证口径是：**四道物理题，一道作者资格通过，三道仍待完成。** 当前专家已接受四份数值参考，见上方更新；不重写下列历史证据。
不再引用“九题三道通过、六道待审”作为本轮工作的进度口径。
四题共有 29 次历史作者原生操作，24 次执行完成、5 次执行失败，全部已回收释放。
24 次中包括错误物理反例与未收敛参考，不能除以 29 当作题目合格率或模型通过率。

## 配置已按新范围调整

- [science.yaml](../experiments/science.yaml)：默认任务为 s-205、s-203、s-202、s-204，删除 s-105；准备名称改为新范围名称，`release.ready` 仍为 false。
- [作者封装清单](../experiments/free-mesh-author-release.yaml)：保留九题登记和历史来源，但 s-10x 全部带 `user_declared_intentional_error_out_of_scope` 阻断，不再生成物理发布候选。这里的 `review` 是现有加载门禁状态，不是要求把故意错误题修好。
- [四题只读运行配置](../experiments/free-mesh-20x-closeout.yaml)：保留四题全部历史尝试，不按结果挑选；不运行检查或补算。
- [旧九题清单](../experiments/free-mesh-author-closeout.yaml)和所有 audits 冻结快照原样保留，供历史核对，不作为新的任务选择。

查看四题运行记录，在 AgentCFD 父目录执行：

```bash
PYTHONPATH=AgentCFD_Terminal_Bench .venv-harbor/bin/python \
  AgentCFD_Terminal_Bench/ci_checks/report_author_closeout.py \
  --config AgentCFD_Terminal_Bench/experiments/free-mesh-20x-closeout.yaml --markdown
```

物理证据：[s-202/s-203 详细审阅](FREE_MESH_THERMAL_REVIEW_20260915.md)、
[s-204/s-205 详细审阅](FREE_MESH_BUOYANT_SHOCK_20260915.md)。
旧范围的工程修复与完整测试仍可参考[历史收尾报告](FREE_MESH_NATIVE_FINAL_20260915.md)，但不据其推进 s-10x。

本次仅调整配置、范围标注及相应测试，不改验收器或模型接口。
48 项范围/配置回归通过，记录见 [tests.xml](../audits/free-mesh-20x-scope-20260915-001/tests.xml)；
[四题只读运行快照](../audits/free-mesh-20x-scope-20260915-001/report.md)保留全部 29 次历史操作。
