# Reconstruct a thermally coupled flow in a branching passage

You are given the three-dimensional exterior geometry and dense synthetic observations of velocity, pressure and temperature. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult the provided general documentation and source code.

## Known physical information

Coordinates are in metres. The passage is a connected three-dimensional fluid region, 0.02 m thick. The horizontal passage extends from x = 0 to x = 0.2 with -0.01 <= y <= 0.01. The vertical passage extends from x = 0.2 to x = 0.22 with -0.21 <= y <= 0.21. Both occupy 0 <= z <= 0.02. The openings are at x = 0, y = -0.21 and y = 0.21; the other surfaces are stationary no-slip physical walls, including the thickness faces.

The problem family is single-phase incompressible internal flow with heat transport and temperature-dependent molecular viscosity. Density is 1.2 kg/m3, specific heat is 1000 J/(kg K), and molecular thermal conductivity is 0.0257 W/(m K). The molecular kinematic viscosity at 300 K is 15e-6 m2/s. There is no gravity, radiation, phase change or moving wall. The flow and thermal boundary forcing, the viscosity law away from 300 K, and the closure choices are not supplied: infer and justify a plausible realization using the observations.

Initially the fluid is at rest at 300 K with zero kinematic gauge pressure. Compute to physical time t = 1.5 s. The supplied observations describe only this terminal time; they do not specify a unique driving history. Do not claim to have uniquely recovered parameters or mechanisms that the data cannot distinguish.

## Deliverable

Submit a successful native calculation with velocity, temperature and kinematic pressure saved at t = 1.5 s. Pressure observations have units m2/s2, not Pa. Choose mesh resolution and numerical controls within the execution budget. Your final saved fields must use the physical coordinates in the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, configuration template or long explanation is required. Concise decision summaries during work are welcome; quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable boundary/material parameters. Do not use the target internal field as your initialized or prescribed solution, construct a pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
