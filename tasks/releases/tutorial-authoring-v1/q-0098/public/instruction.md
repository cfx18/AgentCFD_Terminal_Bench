# Reconstruct supersonic inviscid flow over a forward-facing step

You are given the exterior geometry and dense synthetic observations of velocity, absolute pressure and temperature. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs; no volume-mesh prescription or original configuration is supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The fluid region is the extrusion through -0.05 <= z <= 0.05 of the x-y polygon with successive corners (0, 0), (0.6, 0), (0.6, 0.2), (3, 0.2), (3, 1) and (0, 1). The opening at x = 0 spans 0 <= y <= 1, and the opening at x = 3 spans 0.2 <= y <= 1. The boundary contains a forward-facing step: a vertical face at x = 0.6, 0 <= y <= 0.2, followed by the lower downstream face at y = 0.2. The top boundary and the short lower upstream boundary are also impermeable slip boundaries. The problem is two-dimensional; the two z-normal faces represent the front and back of the 2-D model, not viscous walls.

The problem family is transient, single-phase, inviscid compressible flow of a calorically perfect gas. The gas has molecular weight 11640.3 kg/kmol, constant-pressure specific heat 2.5 J/(kg K), zero heat of formation, zero dynamic viscosity and molecular Prandtl number 1. Its specific-gas constant is approximately 0.714283 J/(kg K), giving gamma approximately 1.4. There is no turbulence model, gravity, reaction, radiation, phase change, moving boundary or volumetric source. These deliberately normalized properties make the sound speed approximately 1 m/s at 1 K.

Initially the entire fluid has velocity (3, 0, 0) m/s, absolute pressure 1 Pa and temperature 1 K. The upstream opening maintains that same state, corresponding to approximately Mach 3. The downstream opening is an outflow and has no independently prescribed downstream thermodynamic state. The initial state, upstream state and impermeable slip geometry are known forcing; the precise numerical outflow treatment, mesh and shock-capturing choices are not supplied and must be chosen plausibly from the observations.

Compute to physical time t = 4 s. The supplied observations describe only that terminal time. Inviscid shock thickness and small oscillations are discretization-dependent, and the observations do not uniquely identify a mesh, numerical flux or boundary implementation. The hidden configuration is one realization, not uniquely identifiable ground truth.

## Deliverable

Submit a successful native calculation with velocity, absolute pressure and temperature saved at t = 4 s. Use SI units and preserve the physical coordinates of the supplied geometry. Choose mesh resolution and numerical controls within the execution budget.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or long explanation is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable boundary and material parameters. Do not initialize or prescribe the target terminal fields, construct pointwise or cellwise forcing that pins the interior to the target, or substitute target data for native solver output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a copying or restart task.
