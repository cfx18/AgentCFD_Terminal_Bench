# Reconstruct transient cavitating flow through a rectangular throttle

You are given the three-dimensional exterior geometry and dense synthetic observations of the native flow fields. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult the provided general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The connected fluid region has constant thickness -0.00015 <= z <= 0.00015. From x = 0 to x = 0.005 it spans -0.0025 <= y <= 0.0025; from x = 0.005 to x = 0.007 it contracts to -0.00015 <= y <= 0.00015; and from x = 0.007 to x = 0.017 it again spans -0.0025 <= y <= 0.0025. The openings are the full faces at x = 0 and x = 0.017. Every other surface, including the contraction and expansion shoulders and both thickness faces, is a stationary no-slip wall.

The physical family is transient, isothermal, compressible cavitating flow represented as a homogeneous liquid-vapour mixture, without gravity, heat transfer or moving boundaries. The liquid has reference density 830 kg/m3 and kinematic viscosity 7.831e-6 m2/s; the vapour has reference density 0.14 kg/m3 and kinematic viscosity 4.252e-5 m2/s. The saturation pressure is 4500 Pa. A linear barotropic description uses saturated-liquid density 830 kg/m3, liquid compressibility 5e-7 kg/(m3 Pa), vapour compressibility 2.5e-6 kg/(m3 Pa), and minimum mixture density 0.001 kg/m3.

Initially the fluid is at rest with absolute pressure 30 MPa, density 845 kg/m3 and vapour volume fraction zero. The initial subgrid kinetic energy is 10 m2/s2 and the initial eddy viscosity is zero. The openings and stationary walls are known, but the inlet/outlet pressure or velocity forcing and the turbulence/cavitation closure details are not supplied; infer and justify a plausible realization from the observations. Different forcing histories or closures may be observationally similar, so do not claim that these inferred choices are unique.

Compute to physical time t = 1e-4 s. The supplied fields describe this terminal time and any supplied time averages describe only the averaging history represented in the data. This short transient endpoint is a numerical reconstruction target, not evidence of a statistically stationary flow.

## Deliverable

Submit a successful native calculation with velocity, absolute pressure, density, vapour volume fraction, subgrid kinetic energy and eddy viscosity saved at t = 1e-4 s. Do not create a temperature field: this problem is isothermal. Choose the volume mesh, solver, closure, boundary forcing and numerical controls within the execution budget. Final fields must use the physical coordinates of the supplied geometry.

Give a short final modelling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, mesh topology or reasoning sequence is required. The reference configuration is only one realization and is not uniquely identifiable ground truth.

The target data may be used for analysis and calibration, including physically interpretable boundary, material and closure parameters. Do not initialize or prescribe the interior from a target terminal field, construct pointwise forcing that pins the interior to the observations, or submit transformed target data as native output. Start from the stated physical initial condition. This is a reconstruction task, not a copying or restart task.
