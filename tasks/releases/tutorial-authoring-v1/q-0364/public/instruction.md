# Reconstruct transient cavitating flow through a planar throttle

You are given the three-dimensional exterior geometry and dense synthetic observations of velocity, pressure, density, vapour fraction and turbulence fields. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The fluid region is planar and is represented over -0.00015 <= z <= 0.00015, with no variation normal to the x-y plane. Its cross-section is the union of three rectangles: 0 <= x <= 0.005 with -0.0025 <= y <= 0.0025; 0.005 <= x <= 0.007 with -0.00015 <= y <= 0.00015; and 0.007 <= x <= 0.017 with -0.0025 <= y <= 0.0025. Thus a 5 mm-high passage contracts abruptly to a 0.3 mm-high, 2 mm-long throat and expands back to 5 mm. The full-height faces at x = 0 and x = 0.017 are open. All remaining edges of the x-y cross-section, including both contraction shoulders, are stationary impermeable no-slip walls. The two z-normal faces represent the planar two-dimensional condition; they are not additional no-slip walls.

The physical family is transient, isothermal, pressure-driven cavitating flow represented as a homogeneous barotropic liquid-vapour mixture. The liquid has saturation density 830 kg/m3 and molecular kinematic viscosity 7.831e-6 m2/s. The vapour transport properties use density 0.14 kg/m3 and kinematic viscosity 4.252e-5 m2/s. The saturation pressure is 4500 Pa. A linear barotropic realization may use liquid and vapour compressibility slopes of 5e-7 s2/m2 and 2.5e-6 s2/m2, respectively, with a minimum mixture density of 0.001 kg/m3. The flow is turbulent and Reynolds averaged. There is no temperature or energy field, gravity, heat transfer, species transport, moving wall or external body force.

Initially the fluid is at rest, with absolute pressure 30 MPa, density 845 kg/m3, zero vapour volume fraction, turbulent kinetic energy 10 m2/s2, specific dissipation rate 77200 1/s and zero turbulent kinematic viscosity. These rounded pressure and density values are consistent with the stated liquid barotropic slope.

The left opening is upstream and the right opening is downstream; the flow is driven by an opening-to-opening pressure reduction. The exact pressure levels imposed at the openings, the total-versus-static boundary formulations, their histories, turbulence boundary treatment and closure details are not supplied. Infer and justify a plausible realization from the observations. Different forcing and closure choices can produce similar terminal fields, so do not claim they are uniquely identified.

Compute from the stated initial condition to physical time t = 0.002 s. The observations describe this terminal time. They are a finite numerical reconstruction target and do not by themselves establish a stationary or mesh-converged continuum solution. The archived configuration that generated them is one realization, not uniquely identifiable ground truth.

## Deliverable

Submit a successful native calculation with velocity, absolute pressure, density, vapour volume fraction, turbulent kinetic energy, specific dissipation rate and turbulent kinematic viscosity saved at t = 0.002 s. Use SI units and the physical coordinates of the supplied geometry. Generate your own mesh; the surface geometry is not a volume-mesh prescription. Do not create or report a temperature field for this isothermal problem.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, mesh topology or long explanation is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable opening and material parameters. Do not initialize or prescribe the target internal fields, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a copying or restart task.
