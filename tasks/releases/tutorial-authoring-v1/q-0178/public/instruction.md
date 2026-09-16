# Reconstruct laminar flow and a drag adjoint around a symmetric airfoil

You are given boundary geometry and dense synthetic observations of a steady primal and adjoint flow state. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs; the boundary file is geometry only and does not prescribe a volume mesh. The configuration that generated the observations is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The fluid is the exterior region between the supplied far-field contour and a symmetric NACA 0012 airfoil of 1 m chord, with leading edge at `(0, 0)` and trailing edge at `(1, 0)`. The airfoil reaches approximately `y = +/-0.059707 m`. The two-dimensional model is represented over `0 <= z <= 1 m`; the planes normal to z are two-dimensional empty planes, not physical walls. The airfoil is stationary and no-slip.

The problem family is steady, single-phase, incompressible, isothermal, laminar flow of a Newtonian fluid. Its molecular kinematic viscosity is `0.006 m2/s`. There is no turbulence model, gravity, heat equation, compressibility, phase change, moving wall or volumetric momentum source.

The known free-stream velocity is `(5.996344962, 0.20939698, 0) m/s`, equivalent to a speed of 6 m/s at 2 degrees above the chord. Kinematic gauge pressure uses a zero far-field reference. How inflow and outflow behavior is implemented on different portions of the enclosing contour is not prescribed; infer and justify a plausible treatment from the geometry and observations. The initial primal state is uniform at the stated free-stream velocity with zero kinematic gauge pressure.

The adjoint observations correspond to a drag-like force objective on both airfoil surfaces, directed along the free stream. Its normalization uses reference area `2 m2`, reference density `1.225 kg/m3`, and reference speed `1 m/s`; this density is an objective-normalization constant, not an additional primal-flow material law. The initial adjoint velocity and adjoint kinematic-pressure fields are zero. The exact boundary implementation and numerical strategy are not uniquely identifiable from a single observed state.

The observations describe an accepted terminal state of a steady iteration. They have no physical timestamp: any iteration coordinate associated with the reference calculation is not elapsed time. Do not claim to have uniquely recovered numerical controls or boundary mechanisms that the data cannot distinguish.

## Deliverable

Submit a successful native calculation with primal velocity `U`, kinematic gauge pressure `p`, adjoint velocity `Ua`, and adjoint kinematic pressure `pa` in physical coordinates at the final saved steady state. `U` and `Ua` have units m/s; `p` and `pa` have units m2/s2. Preserve the stated pressure reference instead of silently aligning a constant offset. Choose your mesh, boundary implementation and numerical controls within the execution budget.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver, dictionary recipe, mesh topology or long explanation is required. The supplied state is one numerical realization, not uniquely identifiable ground truth or a continuum-convergence certificate.

The target data may be used for analysis and calibration of physically interpretable choices. Do not initialize or prescribe any target terminal field, construct pointwise or cellwise forcing that pins the interior to the observations, or substitute supplied values for native calculated output. Start from the stated uniform primal state and zero adjoint state. This is a reconstruction task, not a restart or field-copying task.
