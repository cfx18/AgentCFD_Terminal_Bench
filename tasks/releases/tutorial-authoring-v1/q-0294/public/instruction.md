# Reconstruct transient gas-particle separation in a cyclone

You are given the three-dimensional outer boundary in `outer_geometry.stl` and dense native observations of the carrier and dispersed phases. Build and run an OpenFOAM v2306 case that reproduces the observed state. Generate your own volume mesh and case inputs; the surface is geometry, not a volume-mesh prescription. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres and the vertical axis is z. The main vessel is a radius-0.5 cylindrical section over 0 <= z <= 1 joined to a conical section that narrows to radius 0.15 at z = -1. A radius-0.15 axial outlet tube ends at z = 1.1. The tangential rectangular inlet opening lies in the plane x = 0.55, spans 0.25 <= y <= 0.45 and 0.6 <= z <= 1.0, and the circular outlet opening lies in the plane z = 1.1. The bottom is closed. Treat every other surface in the supplied geometry as a stationary, impermeable, no-slip wall. The triangulated file is authoritative where this verbal summary and polygonal approximation differ.

The physical family is transient, isothermal, incompressible air flow coupled two ways to a dense cloud of solid particles. The air is Newtonian with density 1.2 kg/m3 and kinematic viscosity 1.568e-5 m2/s. The particle material density is 1000 kg/m3. Gravity is (0, 0, -9.81) m/s2. There is no heat equation, temperature field, phase change, surface film, or moving wall.

Initially, at t = 0 s, the vessel contains particle-free air at rest with zero kinematic gauge pressure. The initial turbulent kinetic energy is 1 m2/s2 and the initial turbulent kinematic viscosity is zero. The dimensions of kinematic pressure are m2/s2, not Pa.

Gravity, material properties, opening roles, wall motion, and the initial state above are known. The carrier inlet history, outlet realization, particle injection timing, mass loading, injection velocity and size distribution, wall-particle interaction, dense-particle closures, turbulence closure, and stochastic realization are not supplied. Infer and justify a plausible realization from the observations. These choices are not uniquely identifiable from one terminal state, and the reference is one finite numerical realization rather than a unique physical ground truth.

The observations describe physical time t = 7 s. They may include stochastic parcel-level structure; exact parcel identity is not physically identifiable, so prioritize reproducible carrier fields and spatially aggregated dispersed-phase quantities.

## Deliverable

Submit a successful native calculation with the final carrier velocity, kinematic gauge pressure, turbulent kinetic energy, turbulent kinematic viscosity, carrier/particle volume fractions where produced by the selected native model, and the native particle-cloud fields saved at t = 7 s. Preserve physical coordinates and report the units and dimensions of every delivered field. Do not create a temperature field for this isothermal problem.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives, stochastic uncertainty, and verified results. No particular solver, dictionary layout, mesh topology, or long explanation is required.

The target data may be used for analysis and calibration, including physically interpretable inlet, injection, interaction, and closure parameters. Do not initialize or prescribe the interior from the target fields, construct pointwise or cellwise forcing that pins the solution to the observations, seed particles from terminal target locations, or submit transformed target data as native output. Start from the stated physical initial condition. This is a reconstruction task, not a copying or restart task.
