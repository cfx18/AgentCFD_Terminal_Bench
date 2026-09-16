# Reconstruct evaporation in a heated slender cell

You are given the three-dimensional exterior geometry and dense synthetic observations of phase fraction, temperature, velocity and pressure. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The rectangular fluid domain occupies 0 <= x <= 0.010, 0 <= y <= 0.00020 and 0 <= z <= 0.000020. The face at x = 0 is a stationary, impermeable heated wall. The face at x = 0.010 is an open pressure boundary. The four narrow transverse faces represent a reduced-dimensional problem: the intended solution varies only along x, with no physical side-wall resistance or transverse flux.

The problem family is laminar liquid-vapour phase change with constant phase properties. The liquid has density 958.4 kg/m3, specific heat 4216 J/(kg K), dynamic viscosity 9.59e-4 Pa s and molecular Prandtl number 6.62. The vapour has density 0.581 kg/m3, specific heat 2030 J/(kg K), dynamic viscosity 9.0e-6 Pa s and molecular Prandtl number 0.7. The phase enthalpy-reference difference has magnitude 2.26e6 J/kg. Phase change activates near 373.25 K. Gravity and surface tension are zero.

At physical time t = 1.36 s, the fluid is at rest at 373.15 K and 100000 Pa. A planar interface is at x = 0.000503: vapour occupies the heated-wall side and liquid occupies the outlet side. The phase fractions are complementary. The heated wall is held at 378.15 K. The opening has a 100000 Pa pressure reference and, if reverse flow occurs, admits material at 373.15 K. These thermal and pressure boundary forcings are known.

The detailed interfacial mass-transfer kinetics, interface regularisation, pressure treatment and numerical closure choices are not supplied. Infer a physically plausible realization from the observations. Several realizations may be observationally similar, so do not claim that fitted kinetic or numerical parameters are uniquely identifiable.

## Deliverable

Compute to physical time t = 50 s and submit a successful native calculation with liquid and vapour volume fraction, temperature, velocity and pressure saved at that time. Volume fractions are dimensionless, temperature is in kelvin, velocity is in m/s and pressure is in Pa. Choose your own mesh resolution and numerical controls within the execution budget; the supplied geometry does not prescribe a volume mesh. Final saved fields must use the physical coordinates of the supplied geometry.

Give a short final modelling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, configuration template or long explanation is required. The reference is one finite numerical realization, not uniquely identifiable ground truth, and matching it does not by itself establish a unique physical explanation.

The target data may be used for analysis and calibration, including physically interpretable phase-change parameters. Do not initialize or prescribe the target internal fields, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
