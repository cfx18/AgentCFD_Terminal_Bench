# YAML 配置与精简题面：本轮交付和验证

## 完成了什么

|部分|结果|入口|
|---|---|---|
|配置|带中文注释的 harness、模型、题目、预算、文档、认证、发布证据|[science.yaml](../experiments/science.yaml)|
|编译与执行接线|配置生成逐题 JSON 与矩阵；四种选择传到已有真实 factory，不另写推理循环|[campaign_config.py](../ci_checks/campaign_config.py)|
|命令|prepare/check/submit/status；后台控制器不需要 Agent 监控|[使用说明](YAML_CAMPAIGNS.md)|
|任务题面|十道中文物理题面草案，去掉完整字典与实现提示；未替换旧任务|[逐题审阅](../task-drafts/physics-intent-v1/README.md)|
|隔离与审计|新快照不覆盖；绑定生成配置；排除凭据和符号链接；保留模型与客户端身份检查|[快照代码](../ci_checks/freeze_science_runtime.py)|
|状态表|不再写死 Sol 标题；已保存退出凭据优先于残留 running 状态|[矩阵代码](../ci_checks/run_science_matrix.py)|

## 385 项相关测试通过，不代表所有发布资格已通过

最终相关回归为 **382 passed**；需要本地 Unix socket 的 **3 项另外通过**。总计 385 项互不重复的测试。没有真实模型请求、原生 OpenFOAM 求解或付费任务；真实 harness 新版本接口资格仍未执行。

覆盖 YAML 重复键/别名/未知参数拒绝、模型排除、不支持组合拒绝、预算不注入 token 限额、任务选择和顺序、准备后配置漂移、快照防覆盖/防递归/凭据排除、旧 JSON 兼容、四种 harness 在矩阵和单题 CLI 的实际传参、草案发布阻断，以及已有验收、恢复、文档、身份和预算回归。

完整过程保留，没有删除失败记录：

- 第一轮：[54 项入口测试通过](../audits/yaml-physics-review-20260915-tests-001.xml)。
- 扩展回归：[380 通过，3 项因沙箱禁止 socket.bind 失败](../audits/yaml-physics-review-20260915-tests-002.xml)，原文为 `PermissionError: [Errno 1] Operation not permitted`。
- 经授权的本地接口补测：[3 项全部通过](../audits/yaml-physics-review-20260915-local-sockets-001.xml)，外部模型请求在测试中被拦截。
- 最终回归：[382 通过，排除上述单独完成的 3 项](../audits/yaml-physics-review-20260915-tests-003.xml)。

新增测试代码：[test_campaign_config.py](../ci_checks/test_campaign_config.py)。没有将这组测试结果写入付费发布配置冒充新接口资格。

## 尚未完成、不能冒称修好的部分

1. **新物理题尚未上线。**现有 verifier 对某些网格/字典表示做结构匹配，输出比较依赖单元顺序。只删写法提示会制造隐藏限制，因此物理草案始终被阻断，不会回退到旧 prompt。
2. **部分物理条件仍需对齐。**s-202 外边界条件、s-204 压力/质量约束和湍流初值需明确公开；s-103/104 草案允许的网格与旧精确渐变网格不同，不能混为一个版本。详见逐题审阅表。
3. **原订阅传输审计仍有效。**本轮仅修了新入口直接涉及的标题、终态优先级和宿主客户端路径；断流/完成凭据/ultra 并发等缺陷未在此轮全面修复。
4. **能力列表不是资格证明。**非 Codex harness 当前只支持 Kimi-K3 自定义 API；其他模型组合明确拒绝。API 可用性、实时额度、新桥接的真实客户端表现均未查询。

默认 `release.ready=false` 且选择物理草案。prepare/check 已从 `/tmp` 用绝对脚本路径实际检查过，返回明确阻断，无新增实验目录、无模型调用。旧在测任务与历史结果未被改写。
