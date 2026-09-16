# Reconstruct coupled heat transfer and flow in a sealed cavity

You are given the three-dimensional exterior geometry and dense synthetic observations of velocity, pressure and temperature. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all observations and consult the provided general documentation and source code.

## Known physical information

Coordinates are in metres. The cavity occupies 0 <= x <= 0.076, 0 <= y <= 2.18 and -0.26 <= z <= 0.26. It is sealed: all six walls are stationary, impermeable and no-slip, including the front and back walls. This is a genuinely three-dimensional geometry, not an empty-boundary two-dimensional model.

The problem family is buoyancy-driven air flow with heat transfer. Gravity is (0, -9.81, 0) m/s2. Air obeys the ideal-gas equation of state with molar mass 28.96 kg/kmol. Specific heat is 1004.4 J/(kg K), dynamic viscosity is 1.831e-5 Pa s, and molecular Prandtl number is 0.705. There are no openings, moving walls, volumetric heat sources, radiation or phase change. Wall thermal conditions and closure choices are not supplied: infer a plausible realization from the observed fields.

Initially the air is at rest at 293 K and absolute pressure 100000 Pa. These conditions and the cavity volume define its initial mass. The sealed system does not exchange mass with its surroundings. The observations contain absolute thermodynamic pressure, not pressure with the hydrostatic contribution removed.

## Deliverable

Submit a successful native calculation with final velocity, temperature and absolute pressure fields. Choose your mesh, solver, stopping strategy and numerical controls within the budget. The target is an accepted finite numerical state, not a certified continuum or fully converged steady solution. It has no supplied physical timestamp. Do not interpret a reference iteration index as elapsed seconds, and do not try to recover the author's number of iterations.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, configuration template or long explanation is required. Concise decision summaries during work are welcome; reconstruction accuracy does not by itself establish that your physical explanation is uniquely correct.

The target data may be used for analysis and calibration, including physically interpretable boundary/material parameters. Do not use the target internal field as your initialized or prescribed solution, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Initialize from the stated uniform physical condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
