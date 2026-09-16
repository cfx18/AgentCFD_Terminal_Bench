# Reconstruct an oscillated dense particle column

You are given the three-dimensional exterior geometry and dense numerical observations of an incompressible carrier gas and a dense particle cloud. Build and run an OpenFOAM v2306 case that reproduces the observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. At the initial time the column occupies -0.0092 <= x <= 0.0092, -0.0092 <= y <= 0.0092 and 0 <= z <= 0.3. The four long side faces are symmetry planes. The top and bottom are impermeable no-slip end walls. Particles are confined by rebound interactions at every boundary.

The problem family is a transient, isothermal, two-way-coupled dense particle-in-cell calculation. The continuous phase is laminar incompressible air with density 1.2 kg/m3 and kinematic viscosity 1.0e-5 m2/s. Gravity is (0, 0, -9.81) m/s2. The monodisperse spherical particles have diameter 3.0e-4 m and material density 2526 kg/m3. Their normal rebound coefficient is 1 and their wall tangential-friction coefficient is 0.09. There is no heat equation, phase change, mass transfer, particle injection after initialization, or imposed inlet/outlet flow.

The column undergoes prescribed rigid horizontal sinusoidal translation in x, with displacement amplitude 3 m, angular frequency 0.1 rad/s, zero initial displacement, and the corresponding positive initial translational velocity. This translation and gravity are known forcing. How to realize the motion numerically, along with drag, packing, collision-statistics, interpolation, and pressure-velocity closure details, is not supplied; infer and justify a plausible realization from the observations. The forcing period is about 62.832 s, so the requested state is transient and should not be treated as a stationary endpoint.

Initially, carrier velocity and particle velocity are zero and kinematic gauge pressure is zero. The solids are approximately uniformly randomly distributed through the initial column, with mean solids volume fraction 0.299918. One reference realization represents 2,154,750 physical particles, but its parcel sampling and random coordinates are not uniquely identifiable physical ground truth. Use a statistically and physically consistent initialization rather than trying to recover those hidden parcel identities.

Compute to physical time t = 1.0 s. The observations describe this terminal time in the native moving-geometry coordinates. Pressure observations, if present, are kinematic pressure in m2/s2, not Pa, and are defined only up to the stated gauge convention. No temperature field belongs to this isothermal problem.

## Deliverable

Submit a successful native calculation with the observed carrier velocity, kinematic pressure, phase-volume information, and particle-cloud state saved at t = 1.0 s. Preserve physical coordinates and report represented particle count and mass. Choose the volume mesh, parcel sampling, numerical controls, and physically defensible closure realization within the execution budget.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives, and verified results. The original setup is one numerical realization and is not uniquely identifiable from one transient snapshot. No particular solver, dictionary recipe, mesh topology, parcel identity mapping, or long explanation is required.

The target data may be used for analysis and calibration, including physically interpretable forcing and closure parameters. Do not initialize or prescribe the solution from the target terminal fields, construct pointwise interior forcing that pins the calculation to the observations, reuse target particle coordinates as an endpoint prescription, or substitute target data for native output. Start from the physical initial condition above. This is a reconstruction task, not a copying or restart task.
