# Reconstruct buoyancy-driven flow and heat transfer in a domed enclosure

You are given the three-dimensional exterior geometry and dense synthetic observations of velocity, temperature, kinematic pressure and turbulence-related fields. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The sealed fluid region is the upper half of an axis-aligned ellipsoidal dome centred at (3, 3, 0), with horizontal semi-axes 3.5 m and vertical semi-axis 4 m, closed by the floor at z = 0. Two axis-aligned rectangular obstructions rise from the floor. Each is 1 m by 1 m in plan and 2.1 m high: one occupies 2 <= x <= 3 and 2 <= y <= 3, and the other occupies 3.5 <= x <= 4.5 and 3 <= y <= 4. Their solid interiors are excluded from the fluid. The dome, floor and obstruction surfaces are stationary, impermeable, no-slip walls. There are no openings.

The problem family is steady, single-phase incompressible buoyant flow with heat transport under the Boussinesq approximation. Gravity is (0, 0, -9.81) m/s2. The Newtonian fluid has molecular kinematic viscosity 1.0e-5 m2/s, thermal expansion coefficient 3.0e-3 1/K, reference temperature 300 K and molecular Prandtl number 0.7. Pressure observations are kinematic pressure in m2/s2, not Pa; no absolute density is specified or required by this formulation. There is no moving wall, mass source, volumetric heat source, radiation or phase change.

Initially the fluid is at rest at 265 K with zero kinematic gauge pressure. The mechanical forcing and gravity are known. Wall thermal forcing, turbulence/transition treatment and associated closure parameters are not supplied: infer and justify a plausible realization using the observations. The data do not uniquely identify these choices, and the configuration that produced them is only one possible realization.

## Observation state and deliverable

The observations describe a steady-solver endpoint and have no physical timestamp. Do not interpret an iteration index as elapsed time. The target is a finite numerical state and is not promised to be a mesh-converged continuum solution or a uniquely identifiable physical ground truth.

Submit a successful native calculation with final velocity, temperature and kinematic pressure fields, together with hydrostatic-reduced pressure and closure fields when those quantities are represented in the supplied observations. Choose mesh resolution, closure, stopping strategy and numerical controls within the execution budget. Your final saved fields must use the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or configuration template is required. Concise decision summaries during work are welcome; reconstruction accuracy does not by itself establish that your inferred forcing or closure is unique.

The target data may be used for analysis and calibration, including physically interpretable wall and material parameters. Do not initialize or prescribe the target internal fields, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
