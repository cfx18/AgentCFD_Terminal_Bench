# Reconstruct turbulent airflow and drag sensitivity around a motorcycle

You are given a three-dimensional solid surface and dense native observations of an incompressible flow state. Build and run an OpenFOAM v2306 case that reproduces the observations. Generate your own volume mesh and case inputs; no volume-mesh prescription is supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web references.

## Known physical information

Coordinates are in metres. The fluid region is the rectangular wind-tunnel volume -5 <= x <= 15, -4 <= y <= 4 and 0 <= z <= 8, excluding the motorcycle solid in `geometry/vehicle_surface.obj.gz`. The supplied solid spans approximately -0.291665 <= x <= 1.75115, -0.350289 <= y <= 0.332267 and -0.00004232 <= z <= 1.35152; the tiny excursion below z = 0 is a surface-geometry tolerance. Use the supplied solid surface as the geometric reference. The motorcycle is stationary and no-slip.

The physical family is steady, single-phase, incompressible turbulent external flow of a constant-property Newtonian fluid. Its molecular kinematic viscosity is 1.5e-5 m2/s. Density is not specified because pressure is represented kinematically; pressure observations have units m2/s2, not Pa. There is no heat equation, temperature field, gravity, buoyancy, rotating part, or volumetric momentum source.

The known streamwise free-stream velocity is (20, 0, 0) m/s. It is imposed at x = -5. The road at z = 0 translates in the same direction at (20, 0, 0) m/s, while the motorcycle remains stationary. Kinematic gauge pressure is fixed to zero at x = 15. The planes y = -4, y = 4 and z = 8 are slip boundaries. These velocity, road and pressure forcings are known. The turbulence closure, turbulence boundary details, outlet treatment, and precise numerical realization are not supplied; infer and justify a plausible realization from the observations.

Initially, velocity is uniformly (20, 0, 0) m/s and kinematic gauge pressure is zero. A one-equation eddy-viscosity working variable is initially uniform at 1.5e-4 m2/s and vanishes on the road and motorcycle. The observations represent one finite terminal state of a steady iterative calculation; they have no physical timestamp. An iteration index is not elapsed time, and the original stopping history is not uniquely identifiable from the terminal fields.

The sensitivity observations, when present, correspond to streamwise drag on the motorcycle. Their scale depends on the objective normalization and turbulence/adjoint realization. Treat those choices as inferential rather than uniquely recovered physics. The original configuration is only one numerical realization compatible with the observations.

## Deliverable

Submit a successful native calculation with the terminal velocity, kinematic pressure, one-equation turbulence working variable, and turbulent kinematic viscosity fields. If reconstructing the supplied drag-adjoint or surface-sensitivity observations, identify the drag normalization and report those fields separately from the physical flow fields. Use physical coordinates in metres and preserve each field's native dimensions. Do not create a temperature field for this isothermal problem.

Choose mesh resolution, turbulence/adjoint closure, stopping strategy and numerical controls within the execution budget. Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, configuration template or long explanation is required.

The target data may be used for analysis and calibration, including physically interpretable boundary, material and closure parameters. Do not initialize or prescribe the solution from the target internal fields, construct pointwise or cellwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
