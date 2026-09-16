# Reconstruct laminar flow and moment sensitivity around a symmetric airfoil

You are given the exterior geometry and dense synthetic observations of a primal incompressible flow and its continuous-adjoint fields. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The body is a symmetric NACA 0012 airfoil with a 1 m chord, leading edge at (0, 0) and trailing edge at (1, 0). The supplied domain is a two-dimensional exterior-flow region represented over 0 <= z <= 1; the z-normal faces are two-dimensional empty boundaries. The upper and lower airfoil surfaces are stationary, impermeable no-slip walls. The remaining outer boundary is a far-field opening.

The primal problem family is steady, single-phase, incompressible laminar flow of a Newtonian fluid. Its kinematic viscosity is 0.006 m2/s. There is no turbulence model, heat equation, gravity, compressibility, moving wall or volumetric momentum source. The known free-stream velocity is (5.996344962, 0.20939698, 0) m/s: 6 m/s at 2 degrees incidence, corresponding to a chord Reynolds number of 1000. The initial velocity is this uniform free stream except where wall conditions apply, and the initial kinematic gauge pressure is zero.

The adjoint observations correspond to the sensitivity of the airfoil's z-directed pitching moment about (0, 0, 0), integrated over both airfoil surfaces. The objective normalization uses reference area 2 m2, reference length 1 m, reference density 1.225 kg/m3 and reference speed 1 m/s. The adjoint velocity and adjoint kinematic-pressure fields start from zero. Exact far-field boundary implementations, pressure gauge handling, discretization and numerical controls are not supplied; infer and justify a plausible realization from the observations.

The observations are at terminal steady-iteration label 6000. This is an iteration/pseudo-time coordinate, not 6000 seconds of physical evolution. The source realization allotted up to 3000 primal iterations followed by up to 3000 adjoint iterations, but the data do not establish a unique stopping history or numerical configuration.

## Deliverable

Submit a successful native calculation with primal velocity U, kinematic pressure p, adjoint velocity Ua and adjoint kinematic pressure pa saved at terminal label 6000. U and Ua have units m/s; p and pa have units m2/s2, not Pa. Use the supplied physical geometry but create your own volume mesh. Choose mesh resolution, boundary realization and numerical controls within the execution budget.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, configuration template or long explanation is required. The target is the finite numerical realization represented by the observations, not a claim of a unique continuum solution.

The target data may be used for analysis and calibration, including physically interpretable boundary and numerical choices. Do not initialize from the target terminal fields, prescribe target values through internal or pointwise boundary forcing, add a field-dependent source that pins the solution to the target, or substitute target data for native output. Begin from the stated uniform primal state and zero adjoint state. This is a reconstruction task, not a copying or restart task.
