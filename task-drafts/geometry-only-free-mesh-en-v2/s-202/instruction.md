# Transient conjugate heat transfer with a resistive contact

Build an OpenFOAM v2306 simulation from the supplied geometry and the physical specification below. Generate your own computational mesh and all case inputs. You may consult the provided general OpenFOAM documentation. No initial case or configuration template is supplied.

## Geometry and materials

The geometry is three-dimensional, in metres, with an outer envelope of -0.1 <= x <= 0.1, -0.04 <= y <= 0.04, and -0.05 <= z <= 0.05. The five closed material surfaces define the regions bottomWater, topAir, heater, leftSolid, and rightSolid. Preserve their physical boundaries without gaps or overlapping material volumes. The exterior surface is an envelope, not a sixth region. The plate thickness is 0.008 m and the central heater half-width in x is 0.013333333333333333 m; the complete shape, including its downward stem, is defined by the supplied surfaces.

Both fluid flows are laminar. Water has constant density 1000 kg/m3, specific heat 4181 J/(kg K), dynamic viscosity 9.59e-4 Pa s, and molecular Prandtl number 6.62. Air is an ideal gas with molar mass 28.9 kg/kmol, specific heat 1000 J/(kg K), dynamic viscosity 1.8e-5 Pa s, and molecular Prandtl number 0.7. All three solids are isotropic, with density 8000 kg/m3, specific heat 450 J/(kg K), and thermal conductivity 80 W/(m K). Use a sensible-enthalpy energy description with zero formation-enthalpy offset.

This is an idealized single-phase problem. Keep water at the stated constant density and material properties even if its local temperature exceeds its usual boiling point. Do not include boiling, phase change, latent heat, radiation, chemical reactions, or added volumetric heat sources. Air density still follows its ideal-gas equation of state. Retain transient heat storage in every region.

## Initial state and fluid openings

Initially every region is at 300 K. Water initially moves at (0.001, 0, 0) m/s and enters through its x = -0.1 m opening at the same velocity and 300 K. Air initially moves at (0.1, 0, 0) m/s and enters through its x = -0.1 m opening at that velocity and 300 K. These are two through-flow passages, not sealed fluid cavities.

Gravity is (0, -9.81, 0) m/s2, with the gravitational height datum at y = 0. Define reduced pressure as p* = p - rho (g dot x). For the constant-density water use a gauge-pressure datum: its initial and right-outlet reduced pressure is 0 Pa; this does not represent a vacuum. For the ideal-gas air use absolute thermodynamic pressure: its initial and right-outlet reduced pressure is 100000 Pa, with thermodynamic pressure and density consistent with the gravitational term and the equation of state. Do not interpret the air pressure as a freely shiftable incompressible gauge.

The x = 0.1 m openings are pressure outlets. During outflow, velocity and temperature have zero normal gradient; during reverse flow, the prescribed velocity is zero and the entering temperature is 300 K. At inlets, pressure is determined consistently with the imposed velocity and gravity. At impermeable walls, pressure is determined consistently with zero normal mass flux.

## Walls and thermal interfaces

All fluid-solid surfaces and exterior fluid walls are stationary, impermeable, no-slip boundaries. The heater's exposed base at y = -0.04 m is held at 500 K starting at t = 0. This is a prescribed temperature, not a prescribed power. All other exterior boundaries, except the fluid openings, are adiabatic.

The heater-leftSolid interface has a single thermal contact resistance per unit area of 2 m2 K/W, corresponding to a 0.001 m layer of conductivity 0.0005 W/(m K). Represent it as a zero-storage interfacial resistance, not an additional meshed material. The heat flux from heater to leftSolid is their interface temperature difference divided by this resistance. Describing both sides of the same interface does not create two resistances in series. Every other material interface has perfect thermal contact: temperature and normal heat flux are continuous, with no mass transfer across solid surfaces.

## Requested result

Compute the transient evolution to t = 100 s. Report the actual region temperatures, velocities, through-flow rates, and thermal storage using the accompanying observation definitions. The independently executed fields also support inspection of contact heat transfer and energy balance. Do not replace transient storage by a steady-state heat-balance assumption. Mesh resolution, time stepping, discretization, and numerical solution strategy are your choices within the execution capabilities stated in the accompanying protocol.
