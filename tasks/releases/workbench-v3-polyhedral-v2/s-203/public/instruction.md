# Pressure-driven branching flow with temperature-dependent viscosity

Build an OpenFOAM v2306 simulation from the supplied three-dimensional geometry. Generate your own mesh and all case inputs. You may consult the provided general OpenFOAM documentation; no initial case or configuration template is supplied.

## Geometry and fluid model

Coordinates are in metres. The horizontal inlet passage occupies 0 <= x <= 0.2, -0.01 <= y <= 0.01; the vertical branch occupies 0.2 <= x <= 0.22, -0.21 <= y <= 0.21. Both extend over 0 <= z <= 0.02. They form one connected fluid region. The inlet is at x = 0, the lower outlet is at y = -0.21, and the upper outlet is at y = 0.21. The thickness faces are physical walls, not a two-dimensional simplification.

Use incompressible flow with density 1.2 kg/m3 and the standard k-epsilon Reynolds-averaged turbulence model with its standard coefficients and smooth-wall treatment. The molecular viscosity follows a Bird-Carreau law with an Arrhenius temperature correction: zero- and infinite-shear kinematic viscosities are both 15e-6 m2/s, the rheological time parameter is 0 s, the power-law index is 1, the temperature coefficient is 0.1 1/K, and the reference temperature is 300 K. The rheological time parameter is not the turbulent kinetic energy. Retain the specified temperature dependence when interpreting this parameter combination.

Solve the temperature energy balance with specific heat 1000 J/(kg K), molecular thermal conductivity 0.0257 W/(m K), and turbulent Prandtl number 1. Include viscous dissipation consistently with the effective stress used in the momentum model. Couple the resulting temperature back to the molecular viscosity. There is no buoyancy, gravity forcing, radiation, phase change, or other imposed heat source.

## Initial and boundary conditions

Initially the fluid is at rest, at 300 K and zero kinematic gauge pressure. Initial turbulent kinetic energy is 0.2 m2/s2 and its dissipation rate is 200 m2/s3. The turbulence model determines the corresponding eddy viscosity; it is not an independently prescribed material constant.

All pressure values below are kinematic pressure, with units m2/s2, not Pa. The inlet total pressure is 10 + 30 t during 0 <= t <= 1 s and remains 40 thereafter. The inlet velocity is pressure-driven rather than prescribed; incoming flow is normal to the opening. The inlet temperature is 315 K, turbulence intensity is 5%, and turbulence mixing length is 0.01 m.

At the lower outlet (outlet1), static kinematic pressure is 10 m2/s2. At the upper outlet (outlet2), it is 0 m2/s2. On either outlet, outflow velocity, temperature, turbulent kinetic energy, and dissipation rate have zero normal gradient. During reverse flow, prescribe zero velocity, temperature 300 K, turbulent kinetic energy 0.2 m2/s2, and dissipation rate 200 m2/s3.

All remaining surfaces, including the two thickness faces, are stationary no-slip, adiabatic walls with zero normal pressure gradient and the corresponding standard smooth-wall turbulence treatment.

## Requested result

Compute to t = 1.5 s. Report the actual temperature and velocity statistics, flow split, enthalpy fluxes, and thermal storage defined in the accompanying observations. In particular, report the volume-mean temperature relative to both the initial 300 K state and the 315 K inlet temperature as specified there. Choose mesh resolution, time stepping, and numerical schemes yourself within the accompanying execution protocol.
