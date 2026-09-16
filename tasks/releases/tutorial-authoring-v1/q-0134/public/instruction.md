# Reconstruct rarefied hypersonic flow over a heated 15-degree ramp

You are given the exterior geometry and dense native observations of a dilute-gas flow. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh, particle population and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The flow is two-dimensional in the x-y plane and is represented by a slab spanning -0.0042 <= z <= 0.0042, with empty front and back faces. Its upper boundary is y = 0.3. The left boundary is x = -0.15242 for 0 <= y <= 0.3. From x = -0.15242 to x = 0, the lower outer boundary is y = 0 and is open to the free stream. From (0, 0) to (0.3048, 0.081670913853), the lower boundary is a stationary solid ramp inclined at 15 degrees. The right boundary is x = 0.3048 for 0.081670913853 <= y <= 0.3. All outer boundaries other than the ramp are open free-stream boundaries.

The physical family is direct simulation Monte Carlo for a dilute, non-reacting binary mixture of N2 and O2. The free-stream and initial number densities are 0.777e20 m^-3 for N2 and 0.223e20 m^-3 for O2. The initial and reservoir state has temperature 300 K and bulk velocity (1736, 0, 0) m/s. The ramp is stationary and maintained at 550 K with Maxwellian thermal molecular reflection.

Use a variable-hard-sphere collision description with Larsen-Borgnakke internal-energy redistribution. N2 molecules have mass 46.5e-27 kg, reference diameter 4.17e-10 m, two internal degrees of freedom and viscosity exponent 0.74. O2 molecules have mass 53.12e-27 kg, reference diameter 4.07e-10 m, two internal degrees of freedom and viscosity exponent 0.77. The collision reference temperature is 273 K and the relaxation collision number is 5.0. There is no specified chemistry, body force or volumetric source.

The geometry, gas properties, initial state, free-stream reservoir and wall thermal forcing above are known. Volume-mesh resolution, particle statistical weight, random realization, sampling choices and numerical controls are not supplied; infer defensible choices from the observations and report them. Because DSMC data contain sampling noise, the supplied state is one numerical realization and does not uniquely identify those choices.

Advance from the stated uniform initial condition to physical time t = 0.02 s. The observations describe that terminal time. They do not establish a unique transient realization or random seed.

## Deliverable

Submit a successful native calculation at t = 0.02 s with the observed macroscopic DSMC fields saved in physical SI units, including the sampled density, velocity, thermal and pressure-related quantities present in the supplied data. Preserve the physical coordinates and the two-dimensional empty-plane interpretation. Choose mesh, particle count and statistical averaging controls within the execution budget.

Give a short final modeling note separating known information, inferred numerical choices, unresolved alternatives and verified results. No particular solver name, dictionary layout, mesh prescription or long explanation is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable boundary, collision and sampling parameters. Do not initialize or prescribe the target internal fields, construct pointwise forcing that pins the interior to the target, reuse target particles as an initial cloud, or substitute target data for native output. Start from the stated uniform molecular-gas condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
