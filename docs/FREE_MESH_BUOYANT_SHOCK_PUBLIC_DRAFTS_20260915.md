# s-204 / s-205 公共题面与接口草案

作者整合材料，不直接将本文整份发送给 Agent。每题正式发布时拆分为 `instruction.md`、`protocol.md`、`observations.md`，仅将对应题的公共三件套和几何文件提供给模型。本文件不包含参考波形数值、正确提交文件或验收阈值。

## s-205：instruction.md

# 隔膜破裂后的可压缩波动

给定几何是一根沿 x 方向的直管，几何单位为 m。请从零建立 OpenFOAM v2306 算例，自行生成网格和所有计算配置，研究隔膜移除后的气体运动。没有初始算例或配置模板；可查询提供的 OpenFOAM 通用文档。

管道范围为 −5 ≤ x ≤ 5 m，横截面范围为 −1 ≤ y,z ≤ 1 m。按一维无黏流动处理，横向没有流动和空间变化。在 t=0 时移除 x=0 处的隔膜，此后该位置不再是实体边界。管道两端采用零法向梯度外推。

初始两侧均静止。左侧 x<0 的绝对压力为 100000 Pa、温度为 348.432 K；右侧 x≥0 的绝对压力为 10000 Pa、温度为 278.746 K。气体满足理想气体状态方程，摩尔质量 28.96 kg/kmol、定压比热 1004.5 J/(kg·K)、生成焓常数 2.544×10⁶ J/kg。动力黏度为零，Pr=1，能量采用显内能描述。

计算到 0.007 s。基于真实原生输出报告密度、绝对压力、温度和轴向速度的空间波形，同时报告质量、轴向动量、总能量及最后一步的能量方程残差。不要用未求解的初值、手写波形或理论解替代数值计算输出。提交与数据格式见随题一起提供的运行协议和观测说明。

## s-205：protocol.md

工作区初始仅提供几何文件；题面、运行协议、观测说明均属于公开输入。网格数量及轴向加密由你决定。此版本原生服务支持直线管道的正交块网格，两个无变化的横向各使用一层单元，不指定轴向单元数。其他网格表示尚未获得此版本执行服务支持。

将本题所需的 OpenFOAM 输入写入工作区。服务只运行登记的原生工具：网格生成、初场设置、网格检查、求解，以及可信的单元中心/体积导出；不执行提交的任意 shell/Python 脚本。求解结束后可读取该次运行返回的字段和日志，自行计算报告。

在 `system/science-action.json` 写入运行请求：`{"action":"run","solver":"rhoCentralFoam"}`。运行接口返回独立的 `run_id`。最终提交使用 `{"action":"report","run_id":"r-000001","measurements":{...}}`，其中 run_id 必须指向你实际完成的运行。每个观测量使用 `{"unit":"单位","value":数值或数组}`；不得增删、重命名观测键，不得提交 NaN/Infinity。重试次数、模型轮次及原生运行预算由实验运行协议单独声明。

## s-205：observations.md

所有量均来自 0.007 s 的实际输出。单元体积记为 V，单元中心位置为 C。体积加权均值为 Σ(V·f)/ΣV，不是单元算术均值。

| 键 | 单位 | 内容 |
|---|---|---|
| final_time | s | 真实终止时刻 |
| cell_count | 1 | 实际单元总数 |
| volume | m3 | ΣV |
| mass | kg | Σ(ρV) |
| axial_momentum | kg m/s | Σ(ρUxV) |
| total_energy | J | Σ([p/(γ−1)+ρ\|U\|²/2]V)，γ=Cp/(Cp−R)，R 为气体常数 |
| U_volume_mean | m/s | 三分量速度体积加权均值，长度 3 |
| transverse_velocity_rms | m/s | √[Σ(V(Uy²+Uz²))/ΣV] |
| last_initial_residual | 1 | 最后一步 rhoE 方程的 Initial residual |
| last_final_residual | 1 | 最后一步 rhoE 方程的 Final residual |
| rho_axial_bin_mean | kg/m3 | 下述 40 个轴向区间的密度均值 |
| p_axial_bin_mean | Pa | 同一 40 区间的绝对压力均值 |
| T_axial_bin_mean | K | 同一 40 区间的温度均值 |
| Ux_axial_bin_mean | m/s | 同一 40 区间的轴向速度均值 |

40 个观测区间固定覆盖 x∈[−5,5]，每区间宽 0.25 m，按 x 递增排列。观测分区不要求计算网格也有 40 格。把实际单元值视为单元内常值，跨观测分区的单元按交叠体积分配权重。横截面积为 4 m²，因此每个轴向单元宽度为 V/4；边界为 Cx±V/8。输出每个区间内的体积加权均值。该定义适用于非均匀轴向网格，且不依赖单元存储顺序。

## s-204：instruction.md

# 封闭三维腔体中的自然对流

根据给定几何，从零建立 OpenFOAM v2306 算例，自行生成网格及所有配置，求封闭腔体中空气的自然对流稳态。几何单位为 m，腔体范围为 0≤x≤0.076 m、0≤y≤2.18 m、−0.26≤z≤0.26 m。没有初始算例或配置模板；可查询提供的 OpenFOAM 通用文档。

六面均为静止无滑移壁面。标记 hot 的 x=0.076 m 壁面保持 307.75 K，标记 cold 的 x=0 壁面保持 288.15 K；其余四面绝热。重力为 (0,−9.81,0) m/s²。无质量进出、无外加体积热源、无辐射换热。

空气满足理想气体状态方程，摩尔质量 28.96 kg/kmol，定压比热 1004.4 J/(kg·K)，动力黏度 1.831×10⁻⁵ Pa·s，Pr=0.705。采用标准 k–ω SST RANS 模型及相应壁面处理，湍流普朗特数为 0.85。

初始空气均匀静止，温度 293 K，绝对压力 100000 Pa，湍动能 3.75×10⁻⁴ m²/s²，比耗散率 0.12 s⁻¹。初始绝对压力与温度确定密闭腔体内的空气质量；不能将压力数值参考的任意平移解释为可以改变气体总质量。

报告真实速度、温度、绝对压力、湍流量、壁面总热流和收敛证据。迭代次数达到上限不等于达到稳态：必须检查残差、相邻输出间的场变化及壁面热量收支。提交与数据格式见随题一起提供的运行协议和观测说明。

## s-204：protocol.md

工作区初始仅提供几何文件；题面、运行协议、观测说明均属于公开输入。此版本支持覆盖给定腔体的三维正交块网格，分辨率与各方向加密由你决定，不规定单元数。其他网格表示尚未获得此版本验收资格。

在 `system/science-action.json` 写入 `{"action":"run","solver":"buoyantSimpleFoam"}`。原生服务独立执行网格生成与检查、求解、单元中心/体积导出，以及调用加载了热物性模型的原生壁面热流后处理。报告时引用真实 run_id，结构为 `{"action":"report","run_id":"r-000001","measurements":{...}}`。

保留实际最终迭代对应的 ASCII 字段，以及至少一次之前的 U/T 输出供稳态检查；最终输出不能用较早写出替代。原生服务提供独立的 wallHeatFlux 字段和壁面面积积分日志，不使用用户提交的计算脚本作为验收证据。每个观测量使用 `{"unit":"单位","value":数值或数组}`，键集合及长度严格见观测说明。

## s-204：observations.md

下列标量均基于最终实际迭代。V 为原生单元体积，体积均值为 Σ(Vf)/ΣV；所有积分和均值必须考虑网格加密。

| 键 | 单位 | 内容 |
|---|---|---|
| final_iteration | 1 | 实际最终迭代编号，不是物理秒数 |
| cell_count | 1 | 实际单元数 |
| volume | m3 | ΣV |
| mass | kg | Σ[pV/(RT)] |
| T_volume_mean | K | 温度体积均值 |
| p_volume_mean | Pa | 绝对压力体积均值 |
| speed_volume_rms | m/s | √[Σ(V\|U\|²)/ΣV] |
| U_volume_mean | m/s | 速度三分量体积均值，长度 3 |
| k_volume_mean | m2/s2 | 湍动能体积均值 |
| omega_volume_mean | 1/s | 比耗散率体积均值 |
| nut_volume_mean | m2/s | 湍流运动黏度体积均值 |
| alphat_volume_mean | kg/(m s) | 湍流热扩散系数体积均值 |
| last_initial_residual | 1 | 最终迭代 p_rgh 最后一次线性求解的 Initial residual |
| last_final_residual | 1 | 对应的 Final residual |
| p_rgh_final_initial_residual | 1 | 同上 p_rgh Initial residual |
| h_final_initial_residual | 1 | 最终迭代 h 方程 Initial residual |
| T_last_write_relative_change | 1 | 最后两次 T 输出之差的体积加权绝对均值，除以温差 19.6 K |
| U_last_write_relative_change | 1 | 最后两次 U 输出之差的体积加权 RMS，除以最终速度 RMS；分母下限 10⁻¹² m/s |
| hot_wall_heat_rate | W | 原生 wallHeatFlux 对 hot 的面积积分 |
| cold_wall_heat_rate | W | 原生 wallHeatFlux 对 cold 的面积积分 |
| frontAndBack_wall_heat_rate | W | 对 frontAndBack 两壁之和 |
| topAndBottom_wall_heat_rate | W | 对 topAndBottom 两壁之和 |
| T_x_bin_mean | K | 沿 x 的 20 个等宽分区温度均值 |
| Uy_x_bin_mean | m/s | 沿 x 的同一分区竖直速度均值 |
| T_y_bin_mean | K | 沿 y 的 20 个等宽分区温度均值 |
| Uy_y_bin_mean | m/s | 沿 y 的同一分区竖直速度均值 |

热量符号使用原生 wallHeatFlux 定义：导热从壁面进入流体为正。必须使用面积积分（单位 W），不能直接相加热流密度（单位 W/m²），也不能用壁面面值算术平均代替面积加权。四个 patch 名与提供的几何标签一致。

x 分区覆盖 [0,0.076]，y 分区覆盖 [0,2.18]，均按坐标递增输出长度 20 数组。每个分区覆盖该方向之外的完整腔体截面；跨分区的单元以交叠体积加权。计算网格不要求与这 20 个观测分区对齐。
