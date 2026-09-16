# 首批原始来源审阅（私有，不进入模型上下文）

依据为 `data/tutorial-science-inventory-v1/private-originals.json` 中的原始文件及
逐文件 SHA256，不是旧注错题，也不是修改后的参考。
本文记录已经读到的条件与风险，不授予付费就绪资格。

## s-101：封闭顶盖驱动流

原始路径：`incompressible/icoFoam/cavity/cavity`。

- icoFoam；初始静止；顶壁沿 x 方向 1 m/s，其余三个面内壁面 noSlip。
- 前后 empty；物理尺寸 0.1 × 0.1 × 0.01 m，20 × 20 × 1 均匀网格，400 单元。
- 运动黏度 nu=0.01 m²/s，对应基于腔宽和顶盖速度的 Re=10，不是常见的 Re=100 示例。
- 压力为运动学压力，初始零，面内壁面 zeroGradient，前后 empty。
- startTime=0、endTime=0.5 s、deltaT=0.005 s，固定步长；每 20 步写出。
- 原版 fvSolution 使用 `pFinal { $p; relTol 0; }`，这是本地字典继承，不能为适配
  旧安全规则把原版参考当非法，也不能通过删除/改写原版来掩盖支持缺失。
- 包含 PDRblockMeshDict、decomposeParDict 等辅助文件，不因未被串行流程读取就判错。
- 上级脚本先运行此原始 cavity，再派生其他细网格/高 Re/裁剪算例。后续派生流程
  中的 mapFields 或参数变更不属于本题，不应应用到参考。

后续必须明示终点和网格支持边界，独立验收最终速度场/抽样量；不能沿用旧
Couette 解析解，也不能只检查顶壁输入或 residual。该题没有现成解析速度剖面。

## s-102：两个非共形块的层流通道

原始路径：`basic/simpleFoam/implicitAMI`。
原始输入集合摘要：`b59323fb186f13f5fdf9a382328333438159ee8a45044e0fc556b6883f355702`。

- simpleFoam，Newtonian，simulationType=laminar；nu=1.5e-5 m²/s。
- blockMesh scale=0.1；左块物理 x∈[0,0.05]、y∈[0,0.1]、z∈[0,0.01] m。
- 右块在 xy 平面的顶点为 (0.05,0)、(0.1,0.1)、(0.1,0.2)、(0.05,0.1) m，
  厚度同为 0.01 m。不能把它误读成两个共线矩形块。
- 左块 2×5×1，右块 2×7×1，共 24 单元；接口 AMI1/AMI2 为 cyclicAMI、
  neighbourPatch 相互配对、transform=noOrdering，接口两侧分割数不同。
- U/p 在接口使用 cyclicAMI，p 的接口声明 useImplicit=true。
- 左侧 U=(1,0,0) m/s；右侧 U 为 inletOutlet，回流值为零；上下 U 为零的
  uniformFixedValue。上下网格 patch 类型是 patch，不能暗中改成湍流壁面模型。
- 压力入口/上下 zeroGradient，右侧 fixedValue=0；前后 U/p 与网格均 empty。
- 初始 U/p 均为零；endTime=100、deltaT=1 是稳态迭代索引，不是物理时间。
  fvSolution 的 SIMPLE 没有 residualControl，因此不能凭“稳态任务”任意提前结束。
- controlDict 原版有 `libs (utilityFunctionObjects)`，需针对固定运行环境审阅标准库。
  不能直接复用禁止一切库的旧 s-001 safety policy。
- transportProperties 中的 DT=4e-5 标注供 laplacianFoam 使用；本题执行 simpleFoam，
  不应把这个未启用的温度扩散配置当作独立的主动热物理任务。

风险：原版只有 24 单元。参考输出可用来定义该离散任务的验收基准，但不能宣称
它是网格无关的高精度物理真值。必须先运行原版，明确观察量、数值支持边界和
物理反例，再制定定量阈值；不能看到模型结果之后调阈值。

## s-103/s-104：稳态与瞬态后向台阶

两题同一组五块 hex 分级网格，共 **12225 单元**，前后 empty。入口
x=-0.0206、y∈[0,0.0254] m；台阶 x=0，下游扩展到 y=-0.0254 m；
末段收缩到 x=0.29、y∈[-0.0166,0.0166] m；厚度 0.001 m。

- Newtonian nu=1e-5 m²/s，RAS/kEpsilon；初始 U/p 为零。
- 入口 U=(10,0,0) m/s，出口 U zeroGradient，上下 noSlip；
  压力入口/上下 zeroGradient，出口为零。
- k 初始及入口 0.375 m²/s²；epsilon 初始及入口 14.855 m²/s³；
  墙面为 kqRWallFunction / epsilonWallFunction / nutkWallFunction。
- nuTilda，以及 s-103 的 omega，是备用场，不是当前模型的额外主动方程。
- s-103 最多 2000 稳态迭代，residualControl 为 p=1e-2、U=1e-3、
  湍流场=1e-3。simpleControl::loop 满足条件后 writeAndEnd，不能强求目录 2000。
- s-103 的标准 streamlines 是可视化，引用固定的
  etc/caseDicts/postProcessing/visualization/streamlines.cfg，不是动量源项。
- s-104 从静止推进至 0.3 s，初始 dt=1e-4 s、maxCo=5、自适应步长，
  每 0.01 s 写出。原版 latestTime 在只有原始 0 目录的新工作区中仍从零开始。
- posY/negY/posYR 是分级列表引用；$p/$U 是字典继承，不是动态代码。

## s-105：三维分支、时变总压和标量源

四个均匀 hex 块：1250、125、1250、1250 单元，共 **3875**。
入口 x∈[0,0.2]、y∈[-0.01,0.01]、z∈[0,0.02] m；分支
x∈[0.2,0.22]，底端 y=-0.21、顶端 y=0.21。前后也是 defaultFaces
无滑移墙面，不是二维 empty。

**原始 ASCII 示意图将两个出口的上下标签画反了。** 以真实 faces 为准：

| 实际位置 | 网格面 | 名称 | 运动学静压 |
|---|---|---|---|
| 底部 y=-0.21 | (6 7 17 16) | outlet1 | 10 m²/s² |
| 顶部 y=+0.21 | (8 18 19 9) | outlet2 | 0 m²/s² |

入口 uniformTotalPressure 的 p0 表为 (0,10)、(1,40)。
v2306 Function1/Table/TableBase.C 明确默认 interpolationScheme=linear、
outOfBounds=CLAMP，因此 0..1 s 线性升压，1..1.5 s 保持 40，不外推到 55。

- pimpleFoam，nu=1e-5 m²/s，RAS/kEpsilon，初始 U/p 为零。
- U 入口 pressureInletOutletVelocity；出口 inletOutlet，回流为零。
- k 初始 0.2，入口强度 5%；epsilon 初始 200，入口 mixingLength=0.01 m；
  墙面使用 k/epsilon/nut 壁函数。
- endTime=1.5 s，初始 dt=0.001 s，maxCo=5，写间隔 0.1 s。
- s 无量纲，初始/入口/出口回流均为零，墙面 zeroGradient。
- scalarTransport.C 显示默认 D=nu+nut（alphaD=alphaDt=1）；全域 specific
  源项显式 +1、隐式 0，逐步解对流扩散。不能禁用 function objects。
- probes 只采 p/U，不替代 s 的真实演化与最后场验收。

## 当前产物与剩余门禁

五题匿名要求草稿在 data/tutorial-science-candidates-v2/；原始字节另存
private-original.json。v1 的 JSON 排序导致重载后 prompt 无法逐字复现，保留作
历史；v2 改为确定排序，没有修改物理条件。

原版宏/标准库/主动标量的安全解析和公开物理约束检查已实现，有原版正例及
物理反例测试。后处理报告模板、定量容差、原生正负/伪造对照及最终发布题包
仍未完成。草稿标有 DRAFT，不能发送给付费模型冒充正式题目。
