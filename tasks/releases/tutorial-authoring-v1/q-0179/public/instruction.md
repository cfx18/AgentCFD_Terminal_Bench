# Reconstruct laminar flow and a lift adjoint around a symmetric airfoil

You are given the exact exterior boundary curves and dense synthetic observations of primal velocity, kinematic pressure, adjoint velocity and adjoint kinematic pressure. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The fluid cross-section is the region inside the supplied far-field curve and outside the supplied symmetric airfoil. The airfoil has chord 1 m, spans 0 <= x <= 1, and has maximum half-thickness approximately 0.059707 m. The cross-section is represented as a two-dimensional domain with empty front and back planes at z = 0 and z = 1 m; this numerical extrusion does not imply three-dimensional end-wall physics. Use the supplied curves as geometry, but construct your own volume mesh.

The problem family is steady, single-phase, constant-property incompressible Newtonian flow. The molecular kinematic viscosity is 0.006 m2/s, and the laminar model family applies. The airfoil is stationary and no-slip. There is no body force, heat transfer, turbulence model, compressibility, moving wall or volumetric source. Pressure is kinematic pressure in m2/s2, not Pa; no temperature field belongs to this problem.

Initially, the primal velocity is uniform at (5.996344962, 0.20939698, 0) m/s and the kinematic gauge pressure is zero. This speed is 6 m/s at 2 degrees to the positive x direction. The adjoint fields initially vanish. Start from these physical initial fields, not from the supplied terminal observations.

The adjoint observations correspond to a force objective on both airfoil surfaces in direction (0.034899496703, -0.999390827019, 0). Its reference area is 2 m2, reference density is 1.225 kg/m3, and objective speed normalizer is 1 m/s. These reference quantities define the objective scaling; the density does not change the constant-density kinematic primal equations. The exact numerical realization of the far-field/open boundary and pressure reference is not separately prescribed. Infer and justify a physically plausible realization consistent with the initial state and observations. Terminal fields do not uniquely identify one boundary-condition implementation or one numerical closure.

The observations represent a terminal steady numerical state and have no physical timestamp. Any stored iteration or time-directory label is a pseudo-time/iteration marker, not elapsed seconds. Reproduce the state to adequate stationarity rather than trying to recover an author-specific iteration count.

## Deliverable

Submit a successful native calculation with primal velocity, kinematic pressure, adjoint velocity and adjoint kinematic pressure saved at the final state. Choose mesh resolution, numerical controls and stopping strategy within the execution budget. Preserve the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or configuration template is required. The original configuration is only one realization compatible with the observations, not uniquely identifiable ground truth.

The target data may be used for analysis and calibration, including physically interpretable boundary and numerical choices. Do not initialize from any target terminal field, prescribe target values pointwise in the interior, construct a pointwise forcing that pins the solution to the target, or substitute target data for native output. This is a reconstruction task, not a copying or restart task.
