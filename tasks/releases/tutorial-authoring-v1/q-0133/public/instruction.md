# Reconstruct rarefied argon flow over a heated right-angle corner

You are given the three-dimensional exterior geometry and dense observations of sampled macroscopic gas fields. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The gas region is the rectangular box 0 <= x <= 0.30, 0 <= y <= 0.18 and 0 <= z <= 0.18. The planes y = 0 and z = 0 are symmetry surfaces for 0 <= x <= 0.05. Downstream of x = 0.05, those planes become two stationary, impermeable thermal walls meeting at a right angle. The planes x = 0, x = 0.30, y = 0.18 and z = 0.18 are open free-stream boundaries.

The problem family is a dilute, single-species, monatomic argon flow in the direct-simulation Monte Carlo regime. Each argon molecule has mass 6.63e-26 kg, effective diameter 4.17e-10 m and no internal degrees of freedom. A variable-hard-sphere description uses reference temperature 273 K and viscosity exponent 0.81. There is no gravity, chemistry, radiation, phase change or moving solid.

Initially the box contains uniform argon with number density 1.0e20 m^-3, translational temperature 300 K and bulk velocity (1936, 0, 0) m/s. The open-boundary reservoir has the same macroscopic state. The two walls are held at 1000 K and use thermal Maxwellian molecular reflection from stationary surfaces. These macroscopic forcing data are known. The volume mesh, particle weighting, stochastic realization, detailed numerical boundary implementation and sampling strategy are not supplied; infer and justify a plausible realization. Different microscopic and numerical choices can produce statistically compatible macroscopic fields.

The observations correspond to the fields written at physical time t = 0.01 s. They represent sampled DSMC statistics accumulated during the transient, not an exact noise-free continuum solution or a uniquely identifiable physical ground truth. In particular, an instantaneous field and a time-averaged field need not agree at the particle-noise level.

## Deliverable

Submit a successful native calculation with number density, mass density, mean velocity, translational temperature and pressure saved at t = 0.01 s, using physical SI coordinates. Retain genuinely sampled fields; do not replace them with analytic profiles or synthetic smoothing. Choose the mesh, particle population, solver controls and statistical averaging within the execution budget.

Give a short final modeling note separating known information, inferred choices, stochastic uncertainty, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary template or long explanation is required. The supplied numerical state is one finite stochastic realization, so reconstruction accuracy does not establish that its hidden mesh, random seed or implementation choices have been uniquely recovered.

The target data may be used for analysis and calibration, including physically interpretable boundary, collision and sampling parameters. Do not initialize or prescribe the target internal fields, construct pointwise forcing that pins the interior to the observations, reuse the target as a restart, or substitute target data for native output. Start from the stated uniform gas state. This is a physical reconstruction task, not a test of copying a sampled field.
