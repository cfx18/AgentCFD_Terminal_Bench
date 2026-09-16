# Reconstruct hypersonic nitrogen flow over an axisymmetric biconic body

You are given the exterior geometry and dense numerical observations of velocity, absolute pressure and temperature in a narrow three-dimensional sector of an axisymmetric flow. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs; the supplied geometry is not a volume-mesh prescription. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web references.

## Known physical information

Coordinates are in metres. The body is aligned with the positive x direction. Its meridional profile starts at the nose (0, 0), follows a nominal 25-degree cone to (0.09208087, 0.042939), then a nominal 55-degree cone to (0.153683, 0.13092), and continues at constant radius to (0.193675, 0.13092). The supplied exterior surface also defines the outer far-field and downstream boundaries. The sector represents an axisymmetric problem; its two azimuthal faces are symmetry-equivalent wedge faces, not physical walls.

The physical family is transient, laminar, single-component compressible nitrogen flow at hypersonic speed. Nitrogen is a perfect gas with molar mass 28.01348 kg/kmol and temperature-dependent heat capacity valid from 100 K to 10,000 K. Molecular viscosity follows Sutherland's law with coefficient 1.458e-6 kg/(m s sqrt(K)) and Sutherland temperature 110 K; the molecular Prandtl number is 0.72. There is no turbulence model, gravity, radiation, chemistry, phase change, moving wall or volumetric source.

The known undisturbed state is absolute pressure 22.74 Pa, temperature 138.9 K and velocity (2713, 0, 0) m/s. With the stated gas model this is approximately Mach 11.30. The body is stationary, has wall temperature 296.1 K, and is in the velocity-slip/temperature-jump regime with momentum and thermal accommodation coefficient 0.85. The wall interaction includes thermal creep and surface-curvature effects. Treat these as physical information; the precise numerical boundary formulation, placement of open boundaries and solver/closure implementation remain modeling choices to infer and justify from the geometry and observations.

The reference clock reports the observations at t = 1.0e-3 s. However, its t = 0 state was already a developed, nonuniform flow, and the preceding startup history is not available. Thus this time is 1 ms of additional evolution, not 1 ms after an impulsive flow start. Choose and disclose a target-independent physically plausible initialization and stopping strategy. Do not claim that the unavailable startup history, exact numerical boundary realization or other mechanisms have been uniquely identified.

## Deliverable

Submit a successful native calculation with velocity in m/s, absolute pressure in Pa and temperature in K saved at the observation state. Choose the volume mesh, numerical controls and stopping interpretation within the execution budget. Preserve the supplied physical coordinates. In addition to the native fields, provide cell-centre coordinates and cell volumes so that dense comparisons can be volume weighted.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, configuration template or long explanation is required. The observations are one finite numerical realization, not uniquely identifiable ground truth and not a certification of mesh convergence or continuum accuracy.

The target data may be used for analysis and calibration of physically interpretable parameters. Do not initialize from the target internal fields, prescribe the target as a boundary or interior solution, construct pointwise forcing that pins the domain to the target, or substitute supplied data for native output. This is a physical reconstruction task, not a restart or field-copying exercise.
