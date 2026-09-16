# Reconstruct compressible two-phase sloshing in a moving tank

You are given the exterior geometry and dense synthetic observations of velocity, absolute pressure, temperature and water volume fraction. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. This is a two-dimensional tank in the y-z plane, represented by a unit computational thickness from x = -0.5 to x = 0.5. Its initial cross-section is the closed polygon with successive vertices (y,z) = (-15,-10), (15,-10), (20,-5), (20,10), (10,20), (-10,20), (-20,10) and (-20,-5). The x-normal front and back faces enforce two-dimensionality. Every edge of the polygon is a closed, impermeable no-slip wall; there are no inlets or outlets.

The problem family is laminar, compressible, immiscible water-air flow with heat transport. Gravity is (0,0,-9.81) m/s2 and surface tension is zero. Air is an ideal gas with molar mass 28.9 kg/kmol, constant specific heat 1007 J/(kg K), dynamic viscosity 1.84e-5 Pa s and molecular Prandtl number 0.7. Water uses a linear compressible perfect-fluid equation of state with reference density 1027 kg/m3 and equation-of-state parameter 3000 J/kg; its molar mass is 18.0 kg/kmol, constant specific heat 4195 J/(kg K), dynamic viscosity 3.645e-4 Pa s and molecular Prandtl number 2.289. There is no turbulence model, phase change or mass source.

Initially the fluid is at rest at 300 K and uniform absolute pressure 1.0e6 Pa. Water volume fraction is one below z = 0 and zero above z = 0, so the lower part of the sealed tank is water and the upper part is air.

The known forcing family is prescribed rigid motion of the complete tank: combined sway in y, heave in z and roll about the x axis, centred at the origin. Its detailed time history and parameterization are not supplied; infer and justify a plausible realization from the observations. Other explanations that are observationally indistinguishable at the terminal time remain possible. The supplied state is a finite transient observation at physical time t = 40 s, not a steady-state target.

## Deliverable

Submit a successful native calculation with velocity in m/s, absolute pressure in Pa, temperature in K and water volume fraction saved at t = 40 s. Use the physical coordinates of the supplied geometry and generate your own mesh. The water volume fraction must remain a transported phase indicator rather than a prescribed terminal interface.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, mesh topology or reasoning sequence is required. The reference calculation is only one numerical realization and does not uniquely identify the forcing history or all modeling choices.

The target data may be used for analysis and calibration of physically interpretable motion or material parameters. Do not initialize or prescribe the target internal fields, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
