# Reconstruct an isothermal gas-particle fluidized bed

You are given the three-dimensional exterior geometry and dense synthetic observations of the carrier-gas velocity, kinematic gauge pressure, carrier volume fraction and particulate phase. Build and run an OpenFOAM v2306 case that reproduces the observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The rectangular column occupies -0.0075 <= x <= 0.0075, -0.075 <= y <= 0.075 and 0 <= z <= 0.45. Gas enters through the bottom plane and leaves through the top plane. The two y-normal faces are stationary no-slip physical walls. The two thin x-normal faces are symmetry planes, so the realization is quasi-two-dimensional but retains a finite 0.015 m thickness.

The problem family is an isothermal, incompressible, laminar gas flow coupled to a dense cloud of monodisperse, noncohesive particles. The gas density is 1.2 kg/m3 and its kinematic viscosity is 1.568e-5 m2/s. Particle material density is 2526 kg/m3 and particle diameter is 0.0025 m. Gravity is (0, 0, -9.81) m/s2. Particle impacts at the boundaries are rebounding; the normal restitution coefficient is 0.97 and the tangential friction coefficient is 0.09. There is no thermal equation, heat transfer, reaction, phase change or particle size distribution.

Initially the gas is at rest with zero kinematic gauge pressure. There are 24750 stationary particles on a regular lattice: five x locations from -0.006 to 0.006, fifty y locations from -0.0735 to 0.0735, and ninety-nine z locations from 0.0015 to 0.2955, with 0.003 m spacing in every direction. Each computational parcel represents one physical particle.

Gravity and the zero-gauge top reservoir are known. The magnitude and precise superficial-versus-interstitial interpretation of the uniform upward bottom gas forcing are not supplied; infer and justify a plausible realization from the observations. Dense-phase drag, particle-stress, isotropization and numerical closure choices are also not uniquely identifiable from one observed state. The observations correspond to physical time t = 5 s. The archived configuration that generated them is one realization, not uniquely identifiable ground truth.

## Deliverable

Submit a successful native calculation with carrier velocity, kinematic gauge pressure, carrier volume fraction and the actual modeled particulate fields saved at t = 5 s. Velocity has units m/s and pressure has units m2/s2, not Pa. Do not create a temperature field for this isothermal problem. Choose mesh resolution and numerical controls within the execution budget; the supplied surface describes only the exterior and does not prescribe a volume mesh.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, configuration template or long explanation is required. Concise decision summaries during work are welcome; reconstruction accuracy does not prove that the inferred forcing or closure is unique.

The target data may be used for analysis and calibration of physically interpretable parameters. Do not initialize from any target terminal field, prescribe target internal values, construct pointwise forcing that pins the interior to the observations, or substitute supplied data for native output. Start from the stated gas and particle initial condition. This is a reconstruction task, not a copying or restart task.
