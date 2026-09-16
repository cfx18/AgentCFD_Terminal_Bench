# Reconstruct dense particle transport through a rotating passage

You are given the exterior geometry and dense synthetic observations of carrier velocity, kinematic pressure, carrier volume fraction and particle volume fraction. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The geometry is a two-dimensional flow model represented by a 0.1 m extrusion in z. Its outer planform is the union of a left passage, 0 <= x <= 0.225 and 0 <= y <= 0.3, and a right passage, 0.225 <= x <= 1.225 and -0.2 <= y <= 0.5. The opening at x = 0 spans 0 <= y <= 0.3; the opening at x = 1.225 spans -0.2 <= y <= 0.5. The remaining outer edges are stationary walls. The z = 0 and z = 0.1 faces are empty-direction computational faces, not physical no-slip walls.

A rotating assembly is centred at (0.225, 0.15) about the z axis. The geometry file gives its t = 0 reference orientation. It has a circular hub of radius 0.0375 m and six zero-thickness radial blades, spaced by 60 degrees, extending to radius 0.125 m. Coincident opposite blade faces in the STL represent the two sides of each thin blade. Neutral STL surface labels do not prescribe boundary conditions or a volume mesh.

The physical family is isothermal incompressible laminar carrier flow with transient, one-way-coupled dense Lagrangian particles and a moving rigid rotor. The carrier density is 1.2 kg/m3 and its molecular kinematic viscosity is 1e-5 m2/s. Particles are monodisperse spheres of diameter 0.005 m and material density 1000 kg/m3. Gravity is (0, -9.81, 0) m/s2. There is no thermal equation, phase change or particle-to-carrier momentum feedback.

Initially the carrier is at rest with zero kinematic gauge pressure and the domain contains no particles. Particles enter through the left opening, and the assembly rotates, but the angular speed and direction, particle injection rate and velocity, detailed carrier conditions at the openings, wall-collision parameters, drag/packing closures and numerical coupling choices are not supplied. Infer and justify one plausible realization from the observations. These unknowns are not uniquely identifiable from one snapshot.

Compute to physical time t = 2 s. The observations are native internal-cell values from one finite transient realization at that time, not a stationary, mesh-independent or uniquely identifiable ground truth. In particular, a few supplied cells contain a reported particle volume fraction greater than one. Treat that as a disclosed overpacking defect in the numerical reference, not as a physically admissible continuum state or a reason to invent a different target.

## Deliverable

Submit a successful native calculation with carrier velocity, kinematic pressure, carrier volume fraction and particle volume fraction saved at t = 2 s. Velocity is in m/s, pressure is in m2/s2, and both fractions are dimensionless. Use the physical coordinates in the supplied geometry and choose your own mesh resolution, moving-interface treatment and numerical controls within the execution budget. Do not create a temperature field for this isothermal problem.

Give a short final modelling note separating known information, inferred forcing and closures, unresolved alternatives, numerical reconstruction quality and physical-validity concerns. No particular reasoning sequence, solver name, configuration template or long explanation is required. The original configuration is only one realization compatible with the observations.

The target data may be used for analysis and calibration of physically interpretable parameters. Do not initialize or prescribe the interior from the target fields, construct pointwise forcing that pins the solution to the observations, or substitute supplied target data for native solver output. Start from the stated physical initial condition. This is a reconstruction task, not a copying or restart task.
