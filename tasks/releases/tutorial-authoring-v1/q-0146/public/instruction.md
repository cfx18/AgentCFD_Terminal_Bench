# Reconstruct buoyancy-driven heat transfer in a sealed room

You are given the three-dimensional exterior geometry and dense synthetic observations of velocity, temperature, kinematic pressure and turbulence-related fields. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The sealed rectangular room occupies 0 <= x <= 10, 0 <= y <= 5 and 0 <= z <= 10. Gravity is (0, -9.81, 0) m/s2. All six boundaries are stationary, impermeable, no-slip physical walls. The surface named `floor` is y = 0, `ceiling` is y = 5, and `fixedWalls` contains the other four sides; these geometric labels do not prescribe their thermal conditions. The surface tessellation is not a volume-mesh prescription.

The problem family is single-phase incompressible buoyancy-driven flow with heat transport under the Boussinesq approximation. The Newtonian fluid has molecular kinematic viscosity 1.0e-5 m2/s, thermal expansion coefficient 3.0e-3 1/K, reference temperature 300 K and molecular Prandtl number 0.7. There are no openings, moving walls, volumetric heat sources, radiation or phase change. Any thermal driving therefore enters through the walls. The wall temperatures or heat fluxes, the spatial extent of any heated or cooled wall region, the turbulence closure and its parameters are not supplied: infer and justify a plausible realization from the observations.

Initially the fluid is at rest at 300 K with zero kinematic gauge pressure. Initial values for any closure variables are part of the inferred model. The observations describe a terminal state from a steady iterative calculation and have no physical timestamp. The reference endpoint index is metadata, not elapsed seconds and not a required iteration count. It is an accepted finite numerical state, not a certified continuum or fully converged steady solution.

The `p` observations are kinematic pressure, in m2/s2, with the hydrostatic contribution included. The additional `p_rgh` observations are the corresponding gravity-reduced kinematic pressure. The pressure reference, wall forcing and closure are not uniquely identifiable from one terminal field, so distinguish observed agreement from a unique physical explanation.

## Deliverable

Submit a successful native calculation with final `U`, `T` and kinematic `p` fields; if your formulation uses reduced pressure, also save a physically consistent `p_rgh`. Save the native closure fields used by your model. Choose your own mesh, boundary realization, closure, stopping strategy and numerical controls within the execution budget. Final fields must use the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver, dictionary recipe, mesh topology or long explanation is required. The supplied target is one numerical realization and does not uniquely identify ground-truth forcing or closure.

The target data may be used for analysis and calibration, including physically interpretable wall and material parameters. Do not initialize or prescribe the interior from the target terminal fields, construct pointwise forcing that pins the interior to the observations, or substitute target data for native solver output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
