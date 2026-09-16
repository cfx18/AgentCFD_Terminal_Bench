# Reconstruct premixed combustion through a rotating annular turbine sector

You are given the three-dimensional exterior geometry and dense synthetic observations of the terminal flow, thermodynamic and combustion fields. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The domain is a 20-degree periodic sector of an annular combustor and two blade rows about the x-axis, representing one of 18 repeated sectors. It extends from x = -0.34 m to x = 0.40 m. A circular feed opening of radius 0.05 m is centred at y = 0.50 m, z = 0 on the upstream plane. The downstream opening is on x = 0.40 m. The supplied surface geometry defines the varying hub and casing contours and the blade surfaces; those surfaces are impermeable walls. One downstream blade region rotates rigidly about the x-axis at 10 rad/s. Periodic-sector faces are not physical walls.

The problem family is compressible premixed turbulent methane-air combustion with temperature-dependent ideal-gas thermodynamics and transport. Gravity is zero. The methane, oxidant and burned-product molecular weights are 16.0428, 28.8504 and 27.6333 kg/kmol, respectively. The stoichiometric air-to-fuel mass ratio is 17.1256918 and the fresh mixture has equivalence ratio 0.7. A Sutherland transport law with coefficient 1.67212e-6 kg/(m s sqrt(K)) and temperature 170.672 K applies to all three mixture constituents. Species sensible thermodynamics are temperature dependent over the supplied temperature range. There is no radiation, phase change or volumetric heat source.

Initially, pressure is 1.0e6 Pa, velocity is (4, 0, 0) m/s, burned-gas temperature is 2400 K and unburned-mixture temperature is 573 K. The domain initially contains burned mixture, while fresh premixed reactants enter through the feed opening. The initial mixture fraction is 0.08341685968, flame-wrinkling factor is 1, laminar flame speed is 0.135 m/s and turbulent kinetic energy is 6 m2/s2. No finite ignition kernel is imposed after the start.

The known steady feed velocity is cylindrical about the x-directed line through y = 0.50 m, z = 0: axial velocity 40 m/s, outward radial velocity 20 m/s and solid-body swirl 12732 rpm. Feed temperature is 573 K and the external pressure level at the outlet is 1.0e6 Pa. Walls are adiabatic and no-slip relative to their local motion. The precise outlet wave treatment, temperature-dependent heat-capacity realization, turbulence and turbulent-combustion closures, flame-speed correlation and numerical treatment of the rotating interface are not supplied; infer physically plausible choices from the observations. Different choices can produce similar terminal fields, so do not claim these mechanisms are uniquely identified.

Compute from the stated initial condition to physical time t = 0.1 s. The observations describe that terminal time only and do not uniquely determine the transient history.

## Deliverable

Submit a successful native calculation with velocity, absolute pressure, temperature and the observed combustion/turbulence fields saved at t = 0.1 s. Use SI units and the physical coordinates of the supplied geometry. Choose mesh resolution and numerical controls within the execution budget.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or configuration template is required. The reference is one finite numerical realization, not a certified continuum solution or uniquely identifiable ground truth.

The target data may be used for analysis and calibration of physically interpretable boundary, material and closure parameters. Do not initialize or prescribe the internal solution from any target field, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
