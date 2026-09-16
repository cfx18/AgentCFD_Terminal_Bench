# Reconstruct an unsteady methane-air flame past an oscillating cylinder

You are given the exterior geometry and dense synthetic observations from one finite numerical realization of an unsteady reacting flow. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The planar channel occupies -0.015 <= x <= 0.050 and -0.006 <= y <= 0.006, excluding a circular cylinder of radius 0.004 centred at (0, 0) in its undisplaced position. The numerical thickness is 0.001 in z, with two-dimensional front and back boundaries. The left opening is divided into a central fuel segment, -0.002 <= y <= 0.002, and two air segments covering the rest of the opening. The full right edge is the outlet. The horizontal channel edges are stationary solid walls.

The cylinder is an impermeable no-slip wall that translates in y with displacement 0.001 sin(2 pi 200 t) m; it does not rotate. The outer channel walls and all openings remain fixed. Thus the cylinder is back at its undisplaced position at the observation time.

The problem family is transient compressible turbulent premixed-combustion modelling for methane and air, with an inhomogeneous perfect-gas mixture, temperature-dependent molecular transport and temperature-dependent heat capacity. The molecular weights of methane, oxidant and burnt products are 16.0428, 28.8504 and 27.6333203887 kg/kmol, respectively. The stoichiometric air-to-fuel mass ratio is 17.1256917852. Gravity is zero. There is no radiation, phase change or conjugate solid region.

Initially the gas has absolute pressure 100000 Pa, temperature 300 K and velocity (2, 0, 0) m/s. It contains oxidant and no fuel, is entirely unburned, and has an unstrained flame speed of 0.135 m/s and flame-wrinkling factor 1. The initial turbulent kinetic energy is 1 m2/s2 and its dissipation rate is 100 m2/s3.

The known boundary forcing is as follows. Air enters both outer left segments at 2 m/s and 300 K. Methane enters the central segment at 0.42003 m/s and 300 K. Both streams are unburned. The right opening is held at 100000 Pa. Solid surfaces are adiabatic. Ignition is centred at (0.006, 0), has a 0.001 m diameter, begins at 0.02 s and acts for 0.04 s.

The turbulence closure, flame-speed and flame-wrinkling closures, ignition implementation details, numerical treatment of the moving mesh, and outlet/backflow scalar treatment are not uniquely determined by the observations and should be inferred and justified. Plausible alternatives may produce similar terminal fields. The supplied data represent one finite numerical realization, not uniquely identifiable ground truth and not a claim of mesh or continuum convergence.

## Deliverable

Compute from the stated initial condition to physical time t = 0.1 s. Submit a successful native calculation with velocity, absolute pressure, temperature, total fuel fraction, unburned-gas fraction, flame-wrinkling factor, unstrained flame speed, turbulent kinetic energy and turbulence dissipation rate saved at that time. Use SI units and physical coordinates from the supplied geometry. Choose your mesh and numerical controls within the execution budget.

Give a short final modelling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, configuration template or long explanation is required. Quantitative reconstruction and the observable modelling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable boundary, ignition and closure parameters. Do not initialize or prescribe any target internal field, construct a pointwise or cellwise forcing that pins the interior to the target, substitute target data for native output, or restart from the target state. This is a reconstruction task, not a test of copying a saved solution.
