# Reconstruct transient radiative heating in a sealed cube

You are given the three-dimensional exterior geometry, dense synthetic observations of the gas state at the observation time, and a temperature trace from a thermocouple at the cube centre. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The fluid occupies the sealed cube 0 <= x <= 1, 0 <= y <= 1 and 0 <= z <= 1. All six faces are stationary, impermeable, no-slip walls.

The fluid is laminar ideal-gas air with molar mass 28.9 kg/kmol, constant specific heat 1000 J/(kg K), dynamic viscosity 1.8e-5 Pa s, and molecular Prandtl number 0.7. Gravity is zero. The gas participates weakly in grey radiation with absorption and emission coefficients of 0.01 1/m; there is no scattering, soot, or independent volumetric emission source. Each wall is opaque, grey-diffuse, perfectly absorbing and emitting, with emissivity and absorptivity 1 and transmissivity 0.

Initially the gas is at rest at 298.15 K and absolute pressure 100000 Pa. At t = 0, every wall is held at 873.15 K; this thermal condition and the stationary walls are the only imposed forcing. The cavity remains sealed, so its initial mass must be conserved.

The thermocouple sensing location is (0.5, 0.5, 0.5) m. Its density is 8908 kg/m3, specific heat is 440 J/(kg K), nominal diameter is 0.001 m, and emissivity is 0.85. The precise convective heat-transfer correlation, radiation angular treatment, numerical closure, and any thermocouple initialization detail not fixed above are not supplied. Infer plausible choices from the observations and state them.

The observation time is t = 90 s. The observations do not uniquely identify a mesh, radiation quadrature, time-integration method, or thermocouple closure. Treat any successful configuration as one plausible realization, not as a uniquely recovered ground-truth setup. Exact symmetry and zero gravity provide no physical mechanism for sustained bulk motion; account for that when interpreting very small observed velocities.

## Deliverable

Submit a successful native calculation with gas velocity, temperature, and absolute pressure saved at t = 90 s, together with the predicted centre-thermocouple temperature history through that time. Choose your own mesh resolution and numerical controls within the execution budget. Final fields must use the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives, and verified results. No particular reasoning sequence, solver name, dictionary recipe, mesh prescription, or long explanation is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable closure parameters. Do not initialize or prescribe the target internal fields, construct a pointwise forcing that pins the interior to the target, substitute target data for native output, or restart from the supplied terminal state. Start from the stated physical initial condition. This is a reconstruction task, not a test of copying a numerical solution.
