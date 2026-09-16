# Reconstruct turbulent flow and lift-adjoint fields around a symmetric airfoil

You are given the exterior geometry of a two-dimensional airfoil domain and dense synthetic observations of the primal and continuous-adjoint flow fields. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs; the supplied surface geometry is authoritative and is not a volume-mesh prescription. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The airfoil has a 1 m chord from approximately (0, 0) to (1, 0), is symmetric about y = 0, and has a maximum half-thickness of approximately 0.0597 m. It is represented as a planar two-dimensional body with unit span in the exported coordinates. The remote boundary is about 15 chord lengths from the airfoil; its exact shape and the airfoil surface are defined by the supplied geometry.

The physical family is steady, single-phase, incompressible external flow of a Newtonian fluid. The molecular kinematic viscosity is 1.0e-5 m2/s. The known turbulence family is one-equation Spalart-Allmaras RANS. There is no energy equation, temperature field, gravity, compressibility, moving wall, or volumetric momentum source. Density does not enter the kinematic flow equations; a value of 1.225 kg/m3 is used only in the stated force-objective normalization.

The known uniform free stream is (59.96344962, 2.09396980, 0) m/s: magnitude 60 m/s at 2 degrees to the chord, corresponding to chord Reynolds number 6.0e6. The airfoil is stationary and no-slip. Initially, velocity is the uniform free stream, kinematic gauge pressure is zero, and the Spalart-Allmaras working variable is 2.5e-4 m2/s away from the wall and zero on the wall. The adjoint velocity, adjoint pressure, and adjoint turbulence variable are initially zero.

The adjoint observations correspond to a surface-force objective on both airfoil sides, projected in direction (0.034899496703, -0.999390827019, 0). Its reference area is 2 m2, density scale is 1.225 kg/m3, and velocity scale is 1 m/s. This objective convention is known. The detailed numerical realization of the remote-boundary condition, discretization, mesh, stopping rule, and adjoint stabilization is not prescribed and must be inferred or chosen consistently. Do not introduce interior forcing to fit the observations.

## Observation time and ambiguity

This is a steady calculation, so the observations have no physical timestamp. They represent one finite terminal numerical state after coupled primal and continuous-adjoint iterations; an iteration label is not elapsed seconds. The original setup is only one realization. Similar terminal fields may arise from different far-field boundary formulations, meshes, numerical schemes, stabilization choices, and stopping criteria, so do not claim those details are uniquely identifiable from the observations.

## Deliverable

Submit a successful native calculation with terminal velocity `U` in m/s, kinematic gauge pressure `p` in m2/s2, Spalart-Allmaras working variable `nuTilda` and turbulent kinematic viscosity `nut` in m2/s, adjoint velocity `Ua` in m/s, adjoint pressure `pa` in m2/s2, and adjoint turbulence variable `nuaTilda` in 1/s. Use the physical coordinates of the supplied geometry and provide your own mesh. Preserve the pressure gauge consistently.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives, and verified results. No particular solver dictionary recipe, solver name, configuration template, or long explanation is required. Reconstruction accuracy does not establish that the chosen numerical realization is uniquely correct.

The target data may be used for analysis and calibration of physically interpretable boundary or model parameters. Do not initialize or prescribe any internal field from the target, construct pointwise forcing that pins the interior to the observations, restart from the target state, or substitute target data for native output. Start from the stated uniform primal and zero adjoint initial conditions.
