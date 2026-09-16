# Reconstruct rotating flow through an annular-sector passage

You are given the three-dimensional exterior geometry and dense synthetic observations of two velocity representations, kinematic pressure and turbulence quantities. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The fluid region is a 90-degree sector of an annular passage aligned with the z axis, extending from z = 0 to z = 0.2. Its nominal inner and outer radii are 0.01 m and 0.10 m, with x >= 0 and y >= 0. The supplied STL is authoritative for the slightly faceted geometry. The two annular end faces are openings, the inner and outer cylindrical surfaces are no-slip walls, and the two radial planes form a rotationally periodic pair; their neutral surface labels do not assign inlet, outlet or wall motion.

The physical family is steady, single-phase, incompressible turbulent flow in a single rotating reference frame. The fluid is Newtonian with molecular kinematic viscosity 1.5e-5 m2/s. Pressure is kinematic gauge pressure in m2/s2, not Pa. There is no gravity, heat-transfer model, temperature field, phase change or moving mesh.

The numerical initial state is uniform frame-relative velocity (0, 0, -10) m/s, kinematic gauge pressure 0 m2/s2, turbulent kinetic energy 0.375 m2/s2, specific dissipation rate 3.5 1/s and eddy viscosity 0 m2/s. Because this is a steady problem, these values are an initial iterate rather than a physical state at t = 0.

The flow is driven by axial through-flow and relative rotation: one cylindrical wall co-rotates with the reference frame and the other is stationary in the laboratory frame. The exact rotation rate, assignment and values of inlet/outlet forcing, pressure reference, turbulence closure and turbulence boundary treatment are not supplied. Infer and justify a plausible realization from the observations. Several configurations may be observationally similar; the hidden realization is one numerical construction, not uniquely identifiable ground truth.

## Deliverable

Submit a successful native steady calculation with absolute velocity `U`, frame-relative velocity `Urel`, kinematic pressure `p`, turbulent kinetic energy `k`, specific dissipation rate `omega` and eddy viscosity `nut` saved at one selected finite steady state. Their required dimensions and units are in the observation schema. There is no target temperature and no physical observation time: the supplied state is a finite steady iteration, and its reference iteration label must not be interpreted as seconds or treated as a required iteration count.

Choose the mesh, boundary names, closure and stopping strategy within the execution budget. Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver, dictionary recipe, source template or long explanation is required.

The target data may be used for analysis and calibration, including physically interpretable boundary, rotation and turbulence parameters. Do not initialize or prescribe the interior from the target fields, construct pointwise forcing that pins the interior to the observations, or substitute target data for native solver output. Start from the stated uniform numerical initialization. This is a reconstruction task, not a test of copying or restarting an existing solution.
