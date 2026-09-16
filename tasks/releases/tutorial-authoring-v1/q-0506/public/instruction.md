# Reconstruct neutral atmospheric flow over flat terrain

You are given the three-dimensional exterior geometry and dense numerical observations of velocity, temperature, kinematic pressure with the hydrostatic contribution removed, and turbulence fields. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult the provided general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The fluid region is a right circular cylinder centred on the vertical z axis, with radius 9961.94698092 m. Its flat lower surface is at z = 20 m and its flat upper surface is at z = 6020 m. The lower disk is stationary, impermeable, flat terrain with aerodynamic roughness length 0.05 m. The upper disk and cylindrical side represent remote atmospheric boundaries; there are no buildings, vegetation, internal solids, or moving surfaces.

The problem family is a steady, single-phase, turbulent atmospheric boundary layer under the Boussinesq approximation. The fluid is Newtonian, with kinematic viscosity 1.5e-5 m2/s, thermal expansion coefficient 3.3e-3 1/K, reference temperature 300 K, laminar Prandtl number 0.9, and turbulent Prandtl number 0.74. Gravity is (0, 0, -9.81) m/s2. Temperature is an active transported field, but the terrain has zero imposed heat flux in this stage. The pressure observation is kinematic pressure with the hydrostatic contribution removed, in m2/s2, not pressure in Pa.

The known large-scale forcing includes a uniform horizontal acceleration (0, 1.978046e-3, 0) m/s2 and a rotation vector (0, 0, 5.65156e-5) 1/s. The exact lateral atmospheric profiles, pressure datum, turbulence closure, ambient-turbulence treatment, and detailed far-field boundary realization are not supplied. Infer and justify a physically plausible realization from the observations. They are not uniquely identifiable from one terminal field.

The target stage was initialized from a developed neutral atmospheric boundary layer produced by a separate periodic precursor. That precursor state and its mapping are not supplied. Before mapping, the nominal placeholders were uniform velocity (0, 15, 0) m/s and temperature 300 K, but they are not the actual developed initial profile. Construct your own physically plausible initial state; do not use the target internal fields as an initial condition.

The observations describe the terminal state of a nominally steady calculation at numerical iteration index 1000. This index is not physical time in seconds. The target is one finite numerical realization, not a claim of a unique continuum solution or a uniquely identifiable forcing history.

## Deliverable

Submit a successful native calculation with velocity, temperature, kinematic pressure with hydrostatic contribution removed, turbulent kinetic energy, turbulence dissipation rate, turbulent kinematic viscosity, and turbulent thermal diffusivity saved at the terminal state. Use the physical coordinates of the supplied geometry. Choose your own mesh, closure, initialization, stopping strategy, and numerical controls within the execution budget.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives, and verified results. No particular solver, dictionary recipe, mesh topology, configuration template, or long reasoning sequence is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable boundary, roughness, forcing, and closure parameters. Do not use the target internal field as your initialized or prescribed solution, impose pointwise forcing that pins the interior to the target, or substitute target data for native output. This is a reconstruction task, not a test of copying or restarting an existing solution.
