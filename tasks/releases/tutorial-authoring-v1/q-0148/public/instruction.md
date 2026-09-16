# Reconstruct buoyancy-driven heat transfer in a sealed room

You are given the three-dimensional exterior geometry and dense synthetic observations of velocity, absolute pressure and temperature. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The room is a rectangular sealed cavity occupying 0 <= x <= 10, 0 <= y <= 5 and 0 <= z <= 10. The floor is at y = 0 and the ceiling at y = 5. All six surfaces are stationary, impermeable, no-slip walls. The supplied surface geometry describes only the exterior boundary and does not prescribe a volume mesh.

The problem family is transient buoyancy-driven air flow with heat transfer. Gravity is (0, -9.81, 0) m/s2. Air is a calorically perfect ideal gas with molar mass 28.9 kg/kmol, constant specific heat 1000 J/(kg K), dynamic viscosity 1.8e-5 Pa s and molecular Prandtl number 0.7. There are no openings, moving walls, volumetric heat sources, radiation or phase change.

Initially the air is at rest at 300 K and 100000 Pa absolute pressure. The initial state and the 500 m3 sealed volume define the initial air mass. Gravity is known external forcing. The wall thermal forcing, possible wall heat storage, and turbulence or laminar closure are not supplied; infer and justify a plausible realization from the observations. The data cannot uniquely distinguish all boundary histories or closure choices.

The observations describe physical time t = 2000 s. They are one finite numerical realization, not a uniquely identifiable ground-truth configuration and not a guarantee of mesh-converged or asymptotically steady physics.

## Deliverable

Submit a successful native calculation with velocity, temperature and absolute pressure saved at t = 2000 s. Velocity is in m/s, temperature in K and pressure in Pa. Choose mesh resolution and numerical controls within the execution budget, while retaining the stated geometry, material properties, gravity, initial condition and endpoint. Final fields must use the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver, dictionary recipe, mesh topology or long explanation is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration of physically interpretable wall and closure parameters. Do not initialize or prescribe the solution from the target internal fields, construct pointwise forcing that pins the interior to the observations, or substitute target data for native solver output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a copying or restart exercise.
