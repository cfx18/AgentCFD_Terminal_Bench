# 定量观测要求

取实际计算至 2 s 的最终场。对单元量 q，体积平均为 sum(V_i*q_i)/sum(V_i)，不是单元数平均。

|字段|单位|定义|
|---|---|---|
|final_time|s|实际最终物理时刻|
|cell_count|1|实际单元数，仅统计，不要求等于某个参考数量|
|volume|m3|实际单元体积之和|
|U_volume_mean|m/s|速度三分量的体积平均，三元素数组|
|Ux_volume_rms|m/s|sqrt(sum(V_i*Ux_i^2)/sum(V_i))|
|transverse_velocity_rms|m/s|sqrt(sum(V_i*(Uy_i^2+Uz_i^2))/sum(V_i))|
|p_volume_mean|m2/s2|实际运动学压力的体积平均|
|ux_final_initial_residual|1|最终时间步最后一次 Ux 方程求解日志的 Initial residual|

残差仅报告，不等于物理正确。报告数值允许 1e-6 绝对误差加 1e-5 相对误差。
物理验收在实际单元坐标比较速度与独立解析基准，并采用体积权重；不按参考单元顺序或网格相似度评分。
速度的体积加权均方根误差和最大绝对误差均须不超过 0.005 m/s；横向速度均方根须不超过 1e-6 m/s。
只有物理条件、真实执行、物理精度和报告真实性全部满足才算通过。
