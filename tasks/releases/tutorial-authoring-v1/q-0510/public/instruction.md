# Reconstruct a two-phase dam break through a porous barrier

You are given the exterior geometry and dense synthetic observations of velocity, hydrostatic-reduced gauge pressure, water volume fraction and porosity. Build and run an OpenFOAM v2306 case that reproduces the observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, web references and source code.

## Known physical information

Coordinates are in metres. The fluid region is a rectangular two-dimensional tank occupying 0 <= x <= 0.892 and 0 <= y <= 0.58, represented over 0 <= z <= 0.001 with no variation through the thickness. The left, right and lower boundaries are impermeable slip walls. The upper boundary is open to atmosphere. The front and back faces are the two-dimensional empty-direction faces.

A porous barrier occupies 0.30 <= x <= 0.59 and 0 <= y <= 0.30. Its void fraction is 0.49. Porous resistance belongs to the calibrated Jensen--Jacobsen--Christensen coastal-structure family, with alpha = 500, beta = 2, gamma_p = 0.34, representative grain diameter d50 = 0.0159 m and Keulegan--Carpenter parameter KC = 128. Treat these as material/model data, not as a volume-mesh prescription.

The fluids are incompressible Newtonian water and air. Water has density 1000 kg/m3 and kinematic viscosity 1.0e-6 m2/s; air has density 1 kg/m3 and kinematic viscosity 1.48e-5 m2/s. Surface tension is zero and the flow family is laminar and isothermal. There is no temperature field to reconstruct.

Initially both phases are at rest. Water fills 0 <= x <= 0.281, 0 <= y <= 0.24 and also forms a shallow layer over 0.281 <= x <= 0.892, 0 <= y <= 0.022; the remainder is air. Initial hydrostatic-reduced gauge pressure is zero. Gravity is the known body force (0, -9.81, 0) m/s2, and the atmospheric pressure reference is 0 Pa gauge. There is no inlet, moving wall or other imposed forcing to infer. Numerical interface treatment, pressure-boundary realization and discretization are modeling choices; use a physically plausible realization consistent with the observations.

The observations describe physical time t = 4 s. This is a transient endpoint, not a claimed steady state. The pressure observations are hydrostatic-reduced dynamic pressure in Pa, not kinematic pressure. The supplied realization and the porous closure calibration are not a unique ground-truth explanation of the observed state; alternative numerically and physically defensible realizations may be observationally similar.

## Deliverable

Submit a successful native calculation with velocity, hydrostatic-reduced gauge pressure, water volume fraction and porosity saved at t = 4 s. Choose mesh resolution and numerical controls within the execution budget. Final fields must use the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, configuration template or long explanation is required. Report conservation and boundedness evidence appropriate to transient two-phase flow; do not interpret successful process exit alone as physical convergence.

The target data may be used for analysis and calibration, including physically interpretable model parameters. Do not initialize or prescribe the interior from a target field, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
