# Natural convection in a sealed three-dimensional cavity

Build an OpenFOAM v2306 simulation from the supplied cavity geometry. Generate your own mesh and all case inputs. You may consult the provided general OpenFOAM documentation; no initial case or configuration template is supplied.

## Geometry, walls, and forcing

The cavity occupies 0 <= x <= 0.076 m, 0 <= y <= 2.18 m, and -0.26 <= z <= 0.26 m. It is fully three-dimensional. All six walls are stationary, impermeable, and no-slip; neither the front nor the back is a symmetry or empty boundary.

The hot wall at x = 0.076 m is held at 307.75 K, and the cold wall at x = 0 is held at 288.15 K. The other four walls are adiabatic. Gravity is (0, -9.81, 0) m/s2. There are no openings, moving walls, imposed volumetric heat sources, or radiative heat transfer.

## Air and initial state

Air obeys the ideal-gas equation of state with molar mass 28.96 kg/kmol. Use constant specific heat 1004.4 J/(kg K), dynamic viscosity 1.831e-5 Pa s, and molecular Prandtl number 0.705. Use the standard k-omega SST Reynolds-averaged turbulence model with standard coefficients, smooth-wall treatment, and turbulent Prandtl number 0.85. Use a sensible-enthalpy energy description with zero formation-enthalpy offset.

Initially the air is at rest, uniformly at 293 K and absolute pressure 100000 Pa. Initial turbulent kinetic energy is 3.75e-4 m2/s2 and specific dissipation rate is 0.12 1/s. The initial pressure, temperature, and cavity volume fix the total gas mass. Conserve that mass as the cavity heats and cools; the evolving mean absolute pressure is not fixed at 100000 Pa. A numerical pressure reference must not change the thermodynamic mass. Wall pressure must remain consistent with impermeability and gravity.

## Requested result

Seek the steady natural-convection solution. Choose the mesh resolution, numerical schemes, and iteration strategy yourself. No particular mesh size or number of iterations defines the physical answer. If the execution budget is reached before strict convergence, report the actual available result and its convergence evidence honestly rather than claiming convergence or withholding the result.

Report the actual temperature and velocity profiles, pressure, turbulence statistics, wall heat-transfer rates, and changes between the final two saved iterates as defined in the accompanying observations. Inspect residuals, field changes, and wall heat balance separately: reaching an iteration limit is not evidence of a steady solution. Iteration numbers are not physical elapsed time.
