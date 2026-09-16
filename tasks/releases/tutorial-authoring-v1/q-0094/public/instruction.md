# Reconstruct compressible flow past a heated cylinder

You are given the exterior geometry and dense synthetic observations of velocity, absolute pressure and temperature. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs; the observation coordinates are not a required mesh. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The problem is two-dimensional in the x-z plane and is represented with a 0.1 m empty-direction thickness, -0.05 <= y <= 0.05. The rectangular far-field domain spans -2 <= x <= 4 and -2 <= z <= 2. A stationary circular cylinder of radius 0.5 m, centred at x = z = 0 with its axis parallel to y, is removed from the fluid region. The geometry files contain the inlet, outlet, lateral far-field surfaces and cylinder surface; their labels identify geometric parts only.

The physical family is steady, single-phase, turbulent compressible flow with heat transfer. The gas is calorically perfect, with molecular weight 28.9 kg/kmol and constant specific heat Cp = 1007 J/(kg K). Its dynamic viscosity follows Sutherland's law with coefficient 1.4792e-6 kg/(m s sqrt(K)) and Sutherland temperature 116 K. There is no gravity, radiation, phase change, volumetric heating or moving solid.

The known forcing is a uniform 1 m/s inflow in the +x direction at 300 K on the left opening, a 100000 Pa absolute-pressure level at the right opening, and a stationary no-slip cylinder held at 450 K. The truncated lateral far-field surfaces are impermeable slip surfaces with zero imposed heat flux. The empty-direction faces enforce the two-dimensional model.

The initial computational state is quiescent gas at 300 K and 100000 Pa absolute pressure. Turbulence closure, turbulence initialization and detailed numerical treatment are not prescribed; infer and justify a plausible realization from the observations. Different meshes, closure choices and mathematically equivalent boundary implementations may reproduce the same observable state. The reference is one finite numerical realization, not uniquely identifiable ground truth.

The observations describe a steady numerical endpoint and have no physical timestamp. A reference iteration label, if encountered in metadata, is not elapsed time and need not be reproduced.

## Deliverable

Submit a successful native OpenFOAM calculation with velocity `U`, absolute pressure `p` and temperature `T` saved at your selected steady endpoint. Their units are m/s, Pa and K, respectively. Build your own mesh and choose numerical controls appropriate to the geometry and physics. Your final fields must use the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver, meshing method, dictionary layout or iteration count is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration of physically interpretable parameters. Do not initialize or prescribe the internal solution from target fields, add pointwise or cellwise forcing that pins the interior to the observations, or submit copied target values as native output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a restart or field-copying task.
