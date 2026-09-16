# Reconstruct a transient underexpanded compressible jet

You are given the exterior geometry and dense synthetic observations of velocity, absolute pressure and temperature. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs; the supplied surface is geometry only and does not prescribe a volume mesh. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The fluid region is a narrow axisymmetric wedge spanning 0 <= x <= 0.030 m and 0 <= r <= 0.010 m. Its two azimuthal faces are separated by 0.2 degrees and are symmetry/wedge faces. At x = 0, the circular-equivalent core 0 <= r <= 0.005 m is the jet supply opening; the annulus 0.005 <= r <= 0.010 m is a stationary solid surface. The full x = 0.030 m face is open, and the outer surface r = 0.010 m communicates with the ambient. The file `geometry/domain.obj` contains this exterior surface in physical coordinates. Neutral surface groups describe geometric regions but do not prescribe OpenFOAM patch types.

The physical family is a transient, single-species, laminar compressible gas jet. The gas is calorically perfect and obeys the ideal-gas equation of state. Its molar mass is 28.96 kg/kmol, constant-pressure specific heat is 1004.5 J/(kg K), and sensible internal energy is used. Dynamic viscosity follows Sutherland's law with coefficient 1.458e-6 kg/(m s sqrt(K)), Sutherland temperature 110.4 K, and molecular Prandtl number 1. There is no turbulence model, gravity, combustion, radiation, phase change or volumetric source.

The known supply state is axial velocity 315.6 m/s, static absolute pressure 271724 Pa and static temperature 247.1 K. The stationary annulus is held at 297 K. The ambient total pressure and total temperature are 101325 Pa and 297 K. The downstream opening communicates non-reflectingly with that ambient, and the outer radial opening admits the same ambient state. Exact mathematical open-boundary treatments, numerical flux choices and discretization are not prescribed; infer and justify a stable realization consistent with the observations.

The archived calculation did not start from a documented uniform switch-on condition. Its nominal time zero was already a nonuniform, substantially developed restart state, and the earlier startup history is unknown. The observations are at t = 2.0e-5 s relative to that restart, not 20 microseconds after first opening the jet. This makes the prehistory and an equivalent independently generated initialization ambiguous. Choose and disclose a physically defensible initialization or precursor strategy, but do not initialize or prescribe the interior from the target observations.

## Deliverable

Submit a successful native calculation with velocity `U`, absolute thermodynamic pressure `p`, and temperature `T` saved at the observation state. Their units are m/s, Pa and K. Use physical coordinates matching the supplied geometry. Choose your own mesh, solver and numerical controls within the execution budget; no particular solver dictionary recipe or original case structure is required.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. The target is a finite numerical reconstruction of one realization, not proof of a unique boundary treatment, startup history or continuum-converged solution.

The observations may be used for analysis and calibration of physically interpretable parameters. Do not use the target internal field as an initialized or prescribed solution, construct pointwise forcing that pins the interior to the target, map the target into a restart, or substitute target data for native solver output. A precursor must be produced by your own physical calculation.
