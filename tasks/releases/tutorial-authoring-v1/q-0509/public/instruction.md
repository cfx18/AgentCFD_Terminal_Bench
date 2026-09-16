# Reconstruct a one-dimensional evaporating liquid front

You are given the exterior geometry and dense synthetic observations of velocity, temperature, pressure and liquid volume fraction. Build and run an OpenFOAM v2306 case that reproduces the observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation and source code.

## Known physical information

Coordinates are in metres. The domain is a thin rectangular slab occupying 0 <= x <= 0.01, 0 <= y <= 0.0002 and 0 <= z <= 0.00002. The intended physics is translationally invariant in both transverse directions, so this is a one-dimensional phase-change problem along x; the transverse faces are invariance planes rather than material walls. The plane at x = 0 is a stationary impermeable wall, and the plane at x = 0.01 is an open pressure boundary.

The problem family is laminar, incompressible two-phase evaporation with constant properties. Gravity and surface tension are zero. The saturation temperature is 373.15 K. The liquid has density 958.4 kg/m3, kinematic viscosity 1.0e-6 m2/s, specific heat 4216 J/(kg K), thermal conductivity 0.671 W/(m K), and zero reference enthalpy. The vapour has density 0.581 kg/m3, kinematic viscosity 1.0e-5 m2/s, specific heat 2030 J/(kg K), thermal conductivity 0.025 W/(m K), and an enthalpy offset of 2.260e6 J/kg. Treat this offset as the latent-heat scale.

At reference time t = 1.36 s, both phases are at rest and at 373.15 K, with absolute pressure 100000 Pa. A planar interface is located at x = 0.000503 m: vapour occupies the region between the heated wall and the interface, and liquid occupies the remainder of the slab. This prescribed state is the start of the reconstruction; no earlier transient history is supplied.

The known boundary forcing is a fixed wall temperature of 378.15 K at x = 0 and an open-boundary pressure of 100000 Pa at x = 0.01. The heated wall is no-slip. Temperature has no imposed gradient at the opening. There is no body force, volumetric heat source or other imposed thermal forcing. The detailed interfacial mass-transfer closure and its kinetic parameters are not supplied; infer and justify a plausible realization from the observations. Different closure and discretization choices may reproduce the finite numerical target, so the archived realization is not uniquely identifiable ground truth.

## Deliverable

Compute from the stated state at t = 1.36 s to physical time t = 50 s. Submit a successful native calculation with `U` in m/s, `T` in K, absolute `p` in Pa, and `alpha.liquid` as a dimensionless fraction saved at t = 50 s. Generate your own mesh while preserving the physical coordinates and transverse invariance. The supplied surface describes only the exterior geometry and does not prescribe a volume mesh.

Give a short final modeling note separating known information, inferred closure choices, unresolved alternatives and verified results. No particular solver, dictionary recipe, mesh topology or long explanation is required. The target is a finite native numerical reconstruction; agreement with it does not by itself establish continuum convergence or a unique phase-change mechanism.

The target data may be used for analysis and calibration of physically interpretable closure parameters. Do not initialize from the terminal target field, prescribe target values point by point, add a spatial forcing that pins the interior to the target, or substitute supplied observations for native solver output. Start from the stated planar-interface condition at t = 1.36 s.
