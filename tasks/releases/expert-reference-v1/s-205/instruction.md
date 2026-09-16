# Compressible waves following diaphragm removal

Build an OpenFOAM v2306 simulation from the supplied straight-tube geometry. Generate your own mesh and all case inputs. You may consult the provided general OpenFOAM documentation; no initial case or configuration template is supplied.

## Physical domain and initial discontinuity

The tube occupies -5 <= x <= 5 m and -1 <= y, z <= 1 m. Model one-dimensional, inviscid flow: there is no transverse motion or transverse spatial variation. At t = 0 a diaphragm at x = 0 is removed instantaneously. It separates the initial states only and must not remain an impermeable wall during the computation.

Both sides are initially at rest. For x < 0, absolute pressure is 100000 Pa and temperature is 348.432 K. For x >= 0, absolute pressure is 10000 Pa and temperature is 278.746 K. Determine density consistently from these states and the ideal-gas equation of state.

The gas has molar mass 28.96 kg/kmol and constant specific heat at constant pressure 1004.5 J/(kg K). The formation-enthalpy constant is 2.544e6 J/kg. Use a sensible-internal-energy description. Dynamic viscosity is zero and molecular Prandtl number is 1; there is no turbulence, heat conduction, body force, radiation, reaction, or phase change.

At both tube ends use zero-normal-gradient extrapolation of the evolved fields. The transverse boundaries represent absence of transverse variation rather than viscous no-slip walls. Keep the full physical tube cross-section when computing volumes and integrated quantities.

## Requested result

Compute to t = 0.007 s. Report the actual density, absolute pressure, temperature, and axial-velocity waveforms, together with integrated mass, axial momentum, total sensible energy, and residuals as defined in the accompanying observations. Choose the axial mesh resolution, grading, time stepping, and numerical schemes yourself within the accompanying execution protocol. Use the fields produced by the independent OpenFOAM run, not an analytic waveform or an unevolved initial state in place of simulation output.
