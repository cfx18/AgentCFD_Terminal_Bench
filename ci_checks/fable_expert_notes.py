"""Chinese editorial annotations tied to actual response text, not expert labels."""


def n(title,anchor,observation,thinking,decision,action,result,
      issue='未发现本步导致失败的证据。',question='这一步的选择是否合理，是否有值得保留的好做法？'):
    return dict(title=title,anchor=anchor,observation=observation,thinking=thinking,
                decision=decision,action=action,result=result,issue=issue,question=question)


TRUNC='接口截断后适配器拒绝整份响应，没有工具执行；思考或拟调用中的“我要写……”不能记为文件已写。'
NOACTION='无新工具动作、无新文件提交；不是 OpenFOAM 运行失败。'
OVERVIEW='''先看三件事：

1. **自然对流不是“完全不会改”。** 首次报告不通过后，Agent 已提出改用 limitedLinear 0.2，随后被接口截断，修改没有执行。应审阅这个诊断是否合理，不能写成“没有诊断能力”。
2. **温黏度题不是“未理解温度依赖”。** 返回片段已区分“Bird–Carreau 退化成常数”与“Arrhenius 温度因子仍保留”。真正悬而未决的是能量方程／粘性耗散如何配置；检索也没有提供关键文档。
3. **当前没有五题最终通过率。** 两题通过，三题接口中断；只有自然对流留下了一份可审阅的数值验收失败报告。

每题按“看到了什么 → 思考摘要 → 决策 → 实际 action → 结果 → 归因待审”展开。
先读粗体结论和优先步骤，需要核实时再打开证据；不需要先读源码。
检索卡另列实际关键词、返回内容、Agent 是否明确采纳，以及影响了哪个下一步。
'''

NOTES={
's-204':dict(
title='三维封闭腔自然对流',
task='冷热两侧壁驱动三维腔体内空气自然对流；所有墙面无滑移，其他墙面绝热；从零建模、跑到规定迭代数、报告真实物理量。',
outcome='一次报告验收失败；后续被 API 截断，题级结论未完成。',
priority='C04 数值选择 → C06 修复 → C10 验收 → C11/C12 未执行的诊断。',
review='''| 关键设置 | Agent 实际提交 | 隐藏原版 | 专家应判断什么 |
|---|---|---|---|
| U、h、k、omega 对流格式 | bounded Gauss upwind（一阶迎风） | bounded Gauss limitedLinear 0.2 | 数值扩散／离散差异能否解释偏差？这不是边界或材料理解错误的直接证据 |
| 压力线性求解 | PCG + DIC；容差 1e-8 | GAMG + DICGaussSeidel；容差 1e-7 | 固定迭代下的求解路径是否可比？ |
| momentumPredictor | 没有显式写 no | 显式 no | 需要单因素复算，当前不能宣布因果成立 |
| 壁距计算 | 初次缺失，收到错误后补 meshWave | meshWave | 已证实、可自行修复的配置遗漏 |

首次报告：U 的 L2 误差 17.3905%（限 10%）；k 的 Linf 误差 51.4872%（限 50%）。
材料／边界／活动方程检查、报告数字真实性均通过。参考也没有完全收敛，只是第 1000 次迭代的状态。
因此“基准是否过度比较数值路径”须审阅，不能为了找物理失败而直接给模型贴标签。

**尤其看 C11：Agent 已提出切换 limitedLinear 0.2，但响应被截断，没有执行。**
C12 又出现“可能存在真正二维参考”的猜测，而公开任务和参考都是三维；这是待审的思考偏差，未落实为降维修改。
API 中断、数值误差与这条未执行猜测，必须分开记录。''',
native=[['r-000001','启动失败：fvSchemes.wallDist 缺 method，4.089 秒；还未开始正式迭代。','日志送回；C06 添加 meshWave。'],
        ['r-000002','求解完成，189.491 秒；跑到 1000 次迭代，残差未全收敛。','C08–C10 后处理；独立验收指出 U、k 不通过，不提供参考数字。']],
calls=[
n('检查起始工作区','ls -la /work','公开题面、空工作区；没有参考。','','先确认目录内容。','列出 /work 目录。','目录为空；下一次请求开始规划配置。'),
n('识别案例并规划，但被截断','standard OpenFOAM buoyantCavity','已知工作区为空。','凭几何和温度识别为熟悉的 buoyantCavity；回忆数值设置，并思考封闭域压力基准。','计划按熟悉模板创建配置；片段中考虑 pRefValue=1e5。',NOACTION,'第 2 次请求被截断；之后宿主续接同一会话。',TRUNC,'是否存在套模板或混淆 p 与 p_rgh 的风险？这只是计划，不能当成最终提交。'),
n('建立网格和初始场','single shell command','同一会话续接；原文件仍为空。','准备把文件集中写入以提高效率。','先生成网格和八个初始场。','写 blockMeshDict 与 T、U、p、p_rgh、k、omega、nut、alphat。','写文件命令完成；尚未提交 OpenFOAM。'),
n('选择数值设置','bounded upwind divergence','初始场与网格已写。','把 bounded upwind 当作自己记忆中的标准腔体设置，沿用常见松弛因子。','采用一阶迎风、PCG/DIC 压力求解、稳态 SIMPLE。','写材料、重力、湍流模型、控制及数值字典；漏写 wallDist。','文件写成功；其后原生启动发现 wallDist 缺项。','配置遗漏已证实；数值方案与参考不同已证实，但误差因果待审。','这是合理稳健的数值选择、错误模板记忆，还是任务对数值自由度定义不清？'),
n('第一次提交运行','pRefCell/pRefValue','配置文件已写完。','认为封闭域压力锚定、输出间隔及提前收敛设置已处理。','结束本轮，让独立服务运行。','确认 action=run、solver=buoyantSimpleFoam；无新工具命令。','随后 r-000001 网格检查通过，湍流初始化报缺 wallDist.method。','本次提交有配置错误；不是 API 错误或物理验收失败。','应通过哪些提交前自检避免漏项？'),
n('根据原生日志修复壁距设置','wallDist entry','日志指出 kOmegaSST 初始化所需的壁距方法缺失。','明确需要 wallDist，并选 meshWave。','只补壁距计算，再提交。','在 fvSchemes 加 wallDist { method meshWave; }，重写运行 action。','命令成功；此次实际修复已发生。','可验证的原生配置错误恢复。','是否适合作为“从错误日志定位最小修复”的正例？'),
n('第二次提交运行','resubmitted the run action','壁距项已写入。','','结束本轮，交给独立 OpenFOAM。','确认重新提交运行；无额外修改。','r-000002 完成 1000 次迭代。','本次原生运行成功，但不代表物理验收已通过。'),
n('查看真实输出','Run completed at iteration 1000','服务返回完整运行与输出目录。','','读取实际输出，准备后处理。','列出 r-000002 和 1000 时刻文件。','找到真实场和 solver.log；没有伪造运行。'),
n('计算报告数字','/tmp/ex.py','末次全场与日志可读。','','编写后处理，算内部单元统计及最后压力残差。','运行 Python 后处理并写报告 action。','计算命令成功；报告等候独立核验。'),
n('提交报告并承认未收敛','last p_rgh line','自己的后处理输出。','确认残差来自最后时间块、最后一行 p_rgh 求解。','提交报告；明确这不是已经收敛的稳态解。','提交真实统计；没有新建求解。','随后验收：任务物理设置和报告真实性通过；U、k 全场误差不通过。','数值验收失败；是否能归责模型物理理解尚不明确。','未收敛的固定迭代参考是否足以定义这里的错误？'),
n('提出改格式的诊断，但没执行','limitedLinear 0.2','只收到 U、k 检查不通过；没有看到参考数值、文件或误差位置。','怀疑一阶迎风与参考离散不同，且未收敛状态放大数值路径差异；在几种回忆之间比较。','最后倾向改用 limitedLinear 0.2，再运行看反馈。',NOACTION,'响应被截断。原 fvSchemes 没有改，第三次原生运行没有发生。',TRUNC+' 不能写成“Agent 已改但仍失败”。','这个诊断是否合理？是否值得做单因素试验作为后续数据？'),
n('继续诊断，仍未执行','truly 2D reference','同一份 U、k 不通过反馈和上次文件；尚余调用预算。','在松弛、压力容差、离散与未收敛之间反复推测；末尾还猜测参考可能更接近二维。','考虑加强收敛／改格式；没有形成已执行的最终修改。',NOACTION,'再截断；累计 12 次调用，停止原样续接，剩余预算保留。',TRUNC+' “二维参考”是未验证猜测，不是已经把算例改成二维。','是否应标记“无证据猜参考／诊断不聚焦”？哪些猜测有物理依据，哪些应纠正？')]),
's-203':dict(
title='温度依赖黏度与能量输运',
task='加热入口流体，同时保留 Arrhenius 温度–黏度耦合和粘性耗散；本组 Bird–Carreau 参数没有剪切变稀，但不等于完全恒黏度。',
outcome='API 中断；没有生成可提交配置，不能给物理答案打分。',
priority='C03/C04 物理识别；Q01–Q07 检索质量；C05–C07 未验证实现。',
review='''**已经观察到的理解**：C03/C04 将基底黏度退化为常数与仍然存在的温度因子分开；不能说它“根本没理解温度依赖”。
**尚未解决的实现**：energyTransport 的输入字段、粘性耗散是否要用单独 fvOption。模型多次凭记忆推演，但没有读到对应文档或本地源码。
**一条需要审阅的倾向**：C06 因找不到资料，考虑“标准默认实现可能就是验收期望”。这可能滑向默认包含粘性耗散的无依据假设，但没有实际提交，不能记为已漏掉源项。

7 次检索、0 次已执行全文读取。C07 实际已生成读取 Scalar transport 的命令，但因该响应截断，被适配器整批拒绝。
不能把“没读成”写成“没有选择去读”。宽泛关键词返回很多不相关条目；精确 energyTransport 查询为零。
最后两次搜索输出被 Agent 自己裁成前 3000 字节。资料覆盖、检索策略和 API 截断都影响该轨迹，应分开归因。
下方检索卡明确列出每次搜索返回和“是否真正被模型采纳”。''',native=[],
calls=[
n('检查目录并开始查询','ls -la /work','公开题面与空工作区。','','先查看文件，同时查能量输运与耗散。','列出 /work 和 /artifacts，并执行 Q01 组合关键词搜索。','没有初始文件；检索给出大量泛化条目，未定位目标实现。'),
n('精确查能量模块，再查温黏度','ArrheniusBirdCarreau transport model','Q01 没有给出目标实现。','','精确搜索 energyTransport，并搜索完整黏度模型名。','执行 Q02、Q03：energyTransport 零命中，Arrhenius 查询返回泛化条目。','两个搜索命令执行成功，没有查到目标模块专文。','资料缺口／检索相关性问题，不是模型已写错配置。','检索器是否应明确提示无精确命中，或提供目标源码文档？'),
n('区分剪切依赖与温度依赖','Bird-Carreau model collapses','Q01–Q03 均未直接覆盖所需实现。','判断本参数下 Bird–Carreau 基底恒定，温度因子仍调节黏度；担心温度场和能量模块的配置。','保留温度耦合，尝试从能量参数和标量输运寻找类比。','执行 Q04、Q05：查 Cp/kappa/rhoInf 与 scalarTransport。','获得 Scalar transport 摘要，但未直接验证 energyTransport 或粘性耗散。','物理依赖识别有正面证据；实现仍未验证。','是否可保留这段正确的依赖识别作为正例？精确公式仍应对源码核实。'),
n('扩大检索并裁短输出','exp(-alpha*(T-Talpha))','已拿到 scalarTransport 摘要，仍没有目标能量模块文档。','认为温度因子不能删除；重视温度场注册／创建顺序；尝试从标量输运类比实现。','扩大关键词范围查能量输运和 Arrhenius 黏度。','执行 Q06、Q07；两次都用 head -c 3000 裁短输出。','得到更多泛化条目；没有证据表明它验证了目标实现。','检索策略有动作，知识采纳链缺记录；裁短是 Agent 自己的操作。','应使用哪个权威条目？何时应停止无关搜索，承认资料不足？'),
n('凭记忆定位耗散 fvOption','viscousDissipation','已有泛化搜索摘要，没有目标源码。','回忆 viscousDissipation 是 fvOption，讨论它应进入能量方程以及温度–黏度查找时序。','计划按此组织能量项与输运配置。',NOACTION,'思考后响应截断；文件没有写入。',TRUNC+' 思考中说在看源码，不代表真的执行了源码查询。','这套源项单位／方程配对是否正确？需源码核验后再决定训练标签。'),
n('资料缺失下倾向默认实现','standard implementation with default settings','宿主续接；资料仍缺失，没有新搜索结果。','对粘性耗散支持仍不确定；考虑默认实现可能就是要求；还考虑并列多种参数写法。','计划补配置，但关键实现并未得到验证。',NOACTION,'再次截断，没有证据显示它真的遗漏或正确加入耗散项。',TRUNC+' 待审模式：把默认实现当成未核验物理要求的替代。','如果继续，应验证什么而不是继续猜参数？哪些假设必须明确禁止？'),
n('选中文档读取，但动作被适配器拦下','docs.py read d-7ee4','再次续接，无新增物理或检索反馈。','继续确认无剪切变稀但有温度变化；还在 plain number 与带量纲参数、耗散支持之间回忆。','选定 Scalar transport 文档，试图读取前 6000 字符来类比参数写法。','响应确实包含 docs.py read d-7ee4fb189fc30d26e84e --offset 0 --size 6000；另一个 exec_command 为空参数。适配器因 length 拒绝整份响应，两者均未执行。','第三次截断；没有拿到全文，也没有原生提交。',TRUNC+' 这是检索动作被管线阻断，不是 Agent 没想到要读。','是否需要安全地保留截断响应中完整的只读操作，或明确告知模型哪些动作未执行？这次训练标签不能写“拒绝读文档”。')],
queries=[
dict(keyword='energyTransport function object viscous dissipation',goal='寻找能量输运与粘性耗散的直接用法',returned='首屏是 k-ε-φ-f 湍流模型、turbulenceFields、ObukhovLength、声功率与力系数；不是目标能量输运实现。',adopted='没有点名采纳某条。下一次思考明确说文档没有直接覆盖 energyTransport。',effect='C03 转向回忆及温黏度查询，没有据此落地能量方程。',issue='宽泛词导致大量低相关命中；这不是 energyTransport 已被证明不存在。'),
dict(keyword='energyTransport',goal='精确确认是否有目标模块文档',returned='零条。该固定文档集合无法提供此名称的直接条目。',adopted='明确注意到“没有直接覆盖 energyTransport”；这是检索失败的认识，不是新物理知识。',effect='C03/C04 继续搜索并依赖记忆。',issue='资料覆盖缺口；不能把零命中解释成 OpenFOAM 不支持该模块。'),
dict(keyword='ArrheniusBirdCarreau transport model',goal='确认温度依赖黏度模型',returned='主要是 RAS、Polynomial、Thermophysical 等泛化条目；Polynomial 描述温度多项式性质，不是 ArrheniusBirdCarreau 的系数定义。',adopted='没有点名采纳条目。随后对温度因子的判断是模型回忆／推演，不能记成从这些条目检索得到。',effect='C04 保留温度依赖，继续查能量和标量输运。',issue='无目标模型专文，存在无关结果干扰。'),
dict(keyword='energy transport equation function object Cp kappa rhoInf',goal='查能量方程的密度、比热、导热参数',returned='包含 humidityTemperature 等条目，讨论湿空气温度或其他功能，并未给出 energyTransport 的精确配置。',adopted='未记录具体采纳的条目或参数定义。',effect='C05 仍然靠回忆推演 Cp、rho、kappa 与源项，尚未验证。',issue='关键词太宽；不能把相关词出现当成对应参数已确认。'),
dict(keyword='scalarTransport function object',goal='寻找可以类比的标量输运实现',returned='Scalar transport 摘要说明可输运被动标量、使用 fvOptions 源项，并列出 scalarTransport 与 libsolverFunctionObjects.so 的基本写法；这不等同于确认 energyTransport 的能量源项。',adopted='C07 明确选择条目 d-7ee4fb189fc30d26e84e，发出 read 请求，准备类比其参数写法。这证明它选中了该资料，但没有读到全文，不能声称已从全文学到配置。',effect='下一步读取命令已生成，却因响应 length 被适配器整体拒绝；没有产生新的知识观察或文件修改。',issue='接口截断＋适配器整批拒绝使读取未落地；同时须审阅 scalarTransport 类比 energyTransport 的边界。'),
dict(keyword='energy transport',goal='再扩大能量输运检索范围',returned='包含 RAS、Thermophysical、sorptionWallFunction、thermoFoam 等；thermoFoam 摘要描述的是冻结流场热传递求解器，不是所需 function object。',adopted='未记录明确采用的返回知识。',effect='没有新的核验结论；C05 继续凭记忆寻找耗散配置。',issue='Agent 用 head -c 3000 主动裁短输出；服务完整返回不等于模型看到完整页面。'),
dict(keyword='Arrhenius viscosity',goal='再查黏度的温度依赖',returned='前列是 RAS、Polynomial、DDES、DES 混合离散等；没有 Arrhenius 温度因子的直接解释。',adopted='未记录选中条目；模型的 Arrhenius 判断不能标成这次检索的知识产物。',effect='仍无实装，进入截断请求。',issue='同样主动裁短输出；资料缺口与检索策略应分别标注。')]),
's-202':dict(
title='多区域传热与接触热阻',task='搭建水、空气与三个固体区域；保留接触热阻、恒温壁和材料差别，提交耦合传热计算并逐区域后处理。',
outcome='API 中断；只做目录探测，没有原生提交。',priority='C02–C04：计划很长但没有落地；不要把计划当成已做动作。',
review='''原生验收环境先前的“替代数值对照超时”是作者准备问题，不是模型错误；修订后六项资格检查全部通过，才调用 Fable。

Fable 在返回片段里能列出多区域文件、耦合边界、接触热阻和 500 K 恒温壁；这表示它考虑了这些对象，**不表示实现正确**。
三次长规划都被 4096-token 截断；只有最初两条目录探测真正执行。
值得改进的是“计划—落地”的颗粒度，但当前接口窗口会限制它，不能单纯归责模型懒于执行。''',native=[],
calls=[
n('探测工作目录和程序','which blockMesh','题面已说明 OpenFOAM 在独立服务中，不在 Agent 工作区。','','确认起始目录，并尝试探测本地 blockMesh。','列出 /opt、查 blockMesh、列出 /work 与 /artifacts。','blockMesh 未找到、命令退出 127；/work 为空。','不是环境漏装：隔离协议本来就不提供本地求解器。这次探测属于冗余操作。','是否需要训练 Agent 更好遵循已提供的执行边界，避免重复探测？'),
n('规划多区域文件','standard multiRegionHeater','确认目录为空，本地不装求解器。','列举区域文件；注意即使层流，changeDictionary 涉及的 k/epsilon 仍须存在；考虑耦合边界和相对压力。','计划按熟悉的多区域 tutorial 结构一次写入较多文件。',NOACTION,'第 2 次请求截断，0/、constant/、system/ 尚未生成。',TRUNC,'哪些考虑正确？是否应先写最小文件集并增量验证，而非一次长规划？'),
n('续接后继续整套规划','single script','没有新的运行或资料反馈；旧文件仍为空。','规划区域字典、接触热阻与恒温壁；对 changeDictionary 的层次和匹配顺序仍在回忆。','打算用单个 heredoc 脚本写完整案例。',NOACTION,'第 3 次请求再次截断，仍未产生配置。',TRUNC,'哪些结构应先用最小实例确认？不能把这段计划直接当作配置答案。'),
n('再次长规划后停止','large heredoc commands','再次续接；只有原题和相同工作区。','继续列举全套区域设置；讨论写精度、时间步及恒温壁，仍准备大块写入以节约调用。','计划生成单个大脚本。',NOACTION,'第 4 次请求截断；两次续接耗尽，仍无原生提交。',TRUNC,'能否把此轨迹标为“接口限制下的大动作规划失效”，而不是物理建模失败？')]),
's-105':dict(
title='压力驱动分支流与标量源项',task='从零搭建压力驱动分支流、kEpsilon 湍流和被动标量单位源项；运行到 1.5 s 并输出真实统计。',
outcome='通过；一次网格配置错误，经原生反馈自行修复。',priority='C02/C03 初始边界处理 → C07 最小修复；C05 版本语法自查。',
review='''已证实的错误只有初次 defaultFaces 边界顺序：模型把默认收集边界放在列表开头，blockMesh 要求其在最后。
它收到原生报错后只调整该顺序，第二次完整运行。最终 U/p/标量 s 的 L2 误差分别约 1.029%／1.948%／0.750%，通过。
另有一段主动版本自查：先写 model，再在提交前改为 ESI v2306 的 RASModel；这次没有导致运行失败，不能额外计一次错误。
它从形状识别出 TJunction 名称，但没有搜索、联网或读隐藏参考的动作证据。识别名称不等于泄露参考。''',
native=[['r-000001','blockMesh 失败：defaultFaces 已有面或不在列表末尾，约 0.317 秒。','C07 将 defaultFaces 移到最后。'],['r-000002','完整运行到 1.5 s，随后报告及全场检查通过。','C09–C11 从真实输出后处理，没有伪造报告。']],
calls=[
n('检查工作区','ls -la /work','公开题面和空目录。','','先检查文件。','列出 /work 和 /artifacts。','确认没有现成配置。'),
n('识别分支流并创建网格','TJunction tutorial case','已知目录为空。','凭几何识别为熟悉的 TJunction，并计划加入 scalarTransport。','先搭建四块分支网格。','创建目录并写 blockMeshDict，将 defaultFaces 放在开头。','写文件成功；该顺序随后被 blockMesh 拒绝。','已证实的网格配置错误，非物理意图错误。','为什么提前声明 defaultFaces 却漏掉顺序约束？适合怎样的最小反例训练？'),
n('生成六个初始场','unassigned faces','网格字典已写。','还在回忆默认边界如何收集未声明面，未确认列表顺序。','建立流场、湍流和标量初始／边界条件。','写 U、p、k、epsilon、nut、s。','命令完成；没有修正默认边界顺序。','边界收集规则的不确定性已出现，但当时没有验证。','这里应先检验哪条 OpenFOAM 规则？'),
n('设置物性与时间控制','inletOutlet','场文件已生成。','回忆 k/epsilon 的 inletOutlet 是否必须显式给 value。','继续完成输运、湍流和时间控制。','写 transportProperties、turbulenceProperties、controlDict。','命令完成，尚未运行。'),
n('提交前主动检查版本语法','RASModel','已有湍流与控制配置。','区分 ESI v2306 的 RASModel 与另一分支的 model；核对标量源项格式。','先修正版本关键字，再补离散和线性求解。','把 model 改成 RASModel，写 fvSchemes/fvSolution 与运行 action。','实际修改完成；源项及湍流设置后来通过验收。','可作为版本差异主动修复正例；本次不算原生失败。','是否保留“分清 OpenFOAM 分支语法”的正例？'),
n('第一次提交求解','write lands exactly at 1.5','配置已写齐。','认为输出设置能确保最后写到 1.5 s。','结束本轮并等待独立求解。','确认提交 pimpleFoam 运行 action。','随后 blockMesh 报 defaultFaces 顺序错误，未进入正式求解。','错误定位在 C02 的网格配置，不是标量物理。'),
n('最小修复默认边界顺序','defaultFaces comes last','原生日志明确指出默认边界不在末尾。','判断 defaultFaces 必须移至最后。','仅重排边界列表。','用脚本把 defaultFaces 从开头移到最后，保留其他边界。','修改执行成功，并准备再次运行。','已证实的正确恢复动作。','这一最小修复是否适合直接转为有验证的训练正例？'),
n('第二次提交','Fixed: `defaultFaces`','默认边界顺序已修正。','','结束本轮，重提运行。','确认新 action；没有额外改物理设置。','原生完整运行到 1.5 s。'),
n('查看输出目录','Run passed. Now computing','原生服务返回成功与只读输出。','','准备从真实字段计算统计。','列出 r-000002 与 1.5 时刻文件。','找到六个场和日志。'),
n('运行后处理','/work/post/report.py','真实末时刻场和 solver.log 可读。','','提取内部单元统计和压力残差。','写并执行 report.py，提交报告 action。','计算成功；独立验收后确认数字一致。'),
n('结束并报告结果','Values check out','后处理数字已生成。','核对数值量级与最后残差来源。','提交最终报告，不额外求解。','说明实际速度、压力、湍流及标量范围。','随后私有全场和报告检查全部通过，题目结束。')]),
's-205':dict(
title='可压缩激波管',task='设置左右不同压力和温度的气体，解除隔膜后计算激波、接触间断和稀疏波，运行到 0.007 s 并后处理。',
outcome='一次原生提交、一次报告即通过。',priority='C03 初始状态／状态方程；C04 数值选择；C08 物理解读的证据边界。',
review='''实际配置保留左侧 100000 Pa / 348.432 K、右侧 10000 Pa / 278.746 K，用状态方程得到密度。
模型设置了 setFields，因此 0/T 的通用占位值不是最终左右物理初态，不能仅比较它误判。
最终 T/U/p/rho 全场 L2 误差约 1.033%／2.784%／1.301%／0.997%，全部通过。
模型声称看到了三种波，但当前验收是与隐藏原版全场比较，没有另做解析 Riemann 波速定位；不要把这句话升级成已验证的波结构诊断。''',
native=[['r-000001','完整执行 blockMesh、setFields、checkMesh、rhoCentralFoam，求解到 0.007 s，约 1.338 秒。','C06–C08 后处理；报告数字与独立提取一致，物理设置与全场误差通过。']],
calls=[
n('检查空目录','ls -la /work','只有任务说明。','','先看起始文件。','列出 /work。','目录为空。'),
n('搭建网格和初始场','Nothing exists yet','没有预制算例。','确认需要从头创建文件。','先生成 100×1×1 网格与 p/T/U。','写 blockMeshDict 和三个初始场。','命令成功，仍未求解。'),
n('写气体物性和左右初态','constant/thermophysicalProperties','网格与基础场已写。','','采用 perfectGas 等指定热力学配置，用 setFields 指定左右初态。','写 thermophysicalProperties、层流设置、setFieldsDict。','指定了左右 p/T；rho 交给状态方程计算。','没有证据显示此步物理设置错误。','是否正确理解压力、温度和密度不能独立任意指定？'),
n('选择可压缩数值方法','Kurganov flux scheme','物性与初态已配置。','采用自己熟悉的激波管数值组合，并考虑无粘性情形仍需的求解条目。','选 Kurganov 通量、Euler 时间离散、vanLeer 重构；maxCo=0.2。','写 controlDict/fvSchemes/fvSolution 与运行 action。','文件齐备；时间控制目标 0.007 s。'),
n('首次提交','let the service execute','运行 action 已写。','认为时间步设置符合要求。','结束本轮，让独立服务执行。','确认提交 rhoCentralFoam。','随后首次原生运行成功，无格式或启动失败。'),
n('读取真实求解输出','pulling the fields','原生运行成功。','转向读取真实输出做后处理。','查看末时刻字段和日志。','列出 /artifacts/r-000001。','找到 0.007 时刻结果。'),
n('计算后处理量','import re,json,math','末时刻 U、p、T、rho 与日志可读。','','计算全体内部单元统计和最后 rhoE 残差。','执行 Python 后处理并写报告。','得到每个场 100 个单元的数据；报告后被独立核验为一致。'),
n('报告通过并解释波结构','Waves are all present','已生成真实统计。','','报告波结构与数值结果。','提交最终报告，说明左稀疏波、接触间断与右激波。','随后全场与报告检查通过；波结构文字未做独立解析定位验证。','通过是固定离散数值复现通过，不是所有物理解读逐句已验证。','是否需额外波位置、传播速度诊断才能把最后一句作为物理理解正例？')])
}
