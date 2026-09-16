# Reconstruct a rotating atmospheric boundary layer over flat terrain

You are given the three-dimensional exterior geometry and dense cell-centred observations of velocity, temperature, kinematic pressure and turbulence fields. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are Cartesian and in metres. The fluid region is a rectangular atmospheric column occupying -10000 <= x <= 10000, -10000 <= y <= 10000 and 20 <= z <= 6020. Opposite x faces are periodic, as are opposite y faces; they are not physical inlets or outlets. The bottom is stationary, impermeable rough terrain with roughness length 0.30 m. The top is impermeable and shear-free. The exterior OBJ supplies boundary geometry only and does not prescribe a volume mesh.

The problem family is a steady, single-phase incompressible atmospheric flow with a Boussinesq temperature coupling and a two-equation RANS turbulence description. Gravity is (0, 0, -9.81) m/s2. The molecular kinematic viscosity is 1.5e-5 m2/s, the thermal expansion coefficient is 3.0e-3 K-1 about a reference temperature of 300 K, and the laminar Prandtl number is 0.90. The heat-flux condition uses a specific heat of 1005 J/(kg K). There is no vegetation canopy: drag coefficient, leaf-area density and plant heat-source fields are identically zero. There is no radiation, phase change or moving boundary.

The top temperature is fixed at 300 K. The terrain supplies a uniform upward sensible-heat-flux parameter of 1.0e-4 W/m2 under the model's unit-density convention. Gravity, this thermal forcing and the periodic/no-penetration boundary family are known. The exact uniform horizontal momentum forcing, rotational rate, ambient-turbulence treatment, turbulence closure coefficients and numerical stopping history are not supplied; infer and justify a plausible realization from the observations. Horizontally uniform data cannot uniquely distinguish all such choices.

The initial internal state is U = (17.5, 0, 0) m/s, T = 300 K, hydrostatic-reduced kinematic pressure p_rgh = 0 m2/s2, turbulent kinetic energy k = 1.285 m2/s2 and dissipation rate epsilon = 0.1 m2/s3. The initial internal turbulent viscosity and turbulent thermal diffusivity are zero before their models and wall conditions are evaluated. Boundary values must remain consistent with the physical descriptions above.

The observations are an accepted state at steady iteration index 150000, not a physical timestamp. They are finite tutorial outputs but are not claimed to be a mesh-independent or fully stationary continuum solution. Both supplied pressures are kinematic, in m2/s2 rather than Pa: p includes the hydrostatic contribution, while p_rgh has it removed. Their additive gauge is not independently physical.

## Deliverable

Submit a successful native calculation with U, T, p, p_rgh, k, epsilon, nut and alphat saved at your chosen terminal steady state in the supplied physical coordinate frame. Choose the mesh, closure, forcing parameters and numerical controls within the execution budget. The zero Cd, LAD and qPlant observations describe the absence of a canopy and need not be evolved as prognostic fields unless your selected implementation requires them.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe, configuration template or long explanation is required. The archived realization that generated the observations is only one plausible realization and is not uniquely identifiable ground truth.

The target data may be used for analysis and calibration of physically interpretable global parameters. Do not initialize from any target terminal field, prescribe target values as interior initial or boundary data, construct cellwise or pointwise forcing that pins the interior to the observations, or substitute supplied data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a restart or field-copying task.
