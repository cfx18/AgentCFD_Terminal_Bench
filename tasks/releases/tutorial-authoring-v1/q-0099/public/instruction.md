# Reconstruct compressible gas flow driven by a translating conical body

You are given the exterior geometry and dense synthetic observations of velocity, absolute pressure and temperature. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The fluid region is an axisymmetric five-degree wedge about the x-axis. In the z = 0 meridional plane, the chamber spans -0.0075 <= x <= 0 and 0 <= y <= 0.0025; the two wedge planes are z = +/- y tan(2.5 degrees). Initially, a solid conical frustum occupies -0.007 <= x <= -0.0035. Its meridional radius increases linearly from 0.00075 m at x = -0.007 m to 0.002 m at x = -0.0035 m, and both flat end faces are part of the moving solid. The fluid is the chamber volume outside this body. The face at x = -0.0075 m is an opening. The outer face at y = 0.0025 m and the end face at x = 0 are stationary physical walls; the wedge planes impose axisymmetry.

The problem family is transient, laminar, compressible flow of a calorically perfect ideal gas with moving geometry. The gas has molar mass 28.9 kg/kmol, constant specific heat Cp = 1007 J/(kg K), dynamic viscosity 1.0e-3 Pa s and molecular Prandtl number 0.7. There is no gravity, turbulence model, radiation, phase change, volumetric heating or body-force source.

Initially the gas is at rest at 300 K and absolute pressure 100000 Pa. Starting at t = 0, the complete conical body translates at constant velocity (160, 0, 0) m/s without changing shape. It is an adiabatic no-slip moving wall. The outer wall and x = 0 end wall are stationary, adiabatic and no-slip. The x = -0.0075 m opening is connected to a 100000 Pa total-pressure reservoir; gas entering there has temperature 300 K, while outflow is permitted.

The known physical forcing is the body's prescribed translation and the pressure/temperature reservoir at the opening. How the moving domain, open boundary, mesh and numerical closure are realized is for you to infer and justify. The observations are at physical time t = 2.0e-5 s, when the prescribed translation is 0.0032 m. They describe one finite numerical realization and do not uniquely identify a mesh, discretization, time-step history or boundary implementation.

## Deliverable

Submit a successful native calculation with velocity, absolute pressure and temperature saved at t = 2.0e-5 s in the supplied physical coordinates. Choose mesh resolution and numerical controls within the execution budget while respecting the moving geometry and physical data above. The target is a finite transient reconstruction, not a mesh-convergence study or a uniquely identifiable ground-truth model.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, configuration template or long explanation is required. Concise decision summaries during work are welcome; reconstruction accuracy does not by itself establish that the inferred numerical realization is unique.

The target data may be used for analysis and calibration, including physically interpretable boundary or material choices consistent with the information above. Do not initialize or prescribe the interior from the target terminal fields, construct pointwise forcing that pins the interior to the observations, or substitute target data for native output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
