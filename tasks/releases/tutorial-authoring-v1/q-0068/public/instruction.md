# Reconstruct an ignited homogeneous premixed charge

You are given the exterior geometry and dense synthetic observations from a transient premixed-combustion calculation. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs; the original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The computational region is the thin rectangular prism

`0 <= x <= 0.070`, `0 <= y <= 0.035`, `0 <= z <= 0.001`.

It represents a two-dimensional rectangular domain: the faces normal to z are two-dimensional empty faces, while all four in-plane sides are symmetry planes. There are no inlets, outlets or no-slip walls. The supplied exterior surface describes geometry only and does not prescribe a volume mesh or cell count.

The problem family is transient compressible turbulent premixed combustion of a homogeneous stoichiometric propane-air charge. Use an ideal-gas homogeneous-mixture description with temperature-dependent reactant and product thermodynamics. The effective reactant and product molecular weights are 29.4649 and 28.3233 kg/kmol, respectively; the stoichiometric air-to-fuel mass ratio is 15.675. Both states use constant dynamic viscosity 1.0e-5 Pa s and molecular Prandtl number 1. There is no imposed boundary mass flow or boundary heat flux. Gravity, radiation, sprays and phase change are absent.

Initially the gas is at rest at 300 K and uniform absolute pressure 118000 Pa. It is fully unburnt, with total fuel mass fraction 0.06 and equivalence ratio 1. The initial turbulent kinetic energy is 1.5 m2/s2 and its dissipation rate is 375 m2/s3. The initial laminar flame speed is 0.434 m/s and the flame-wrinkling factor is 1.

Ignition is known forcing, not an inferred boundary condition. A 0.003 m diameter ignition kernel is centred at (0, 0, 0.0005), on the intersection of two symmetry planes, starts at t = 0 and acts for 0.003 s. The archived realization used a dimensionless source-strength setting of 2 and a nominal ignition thickness of 0.001 m; their exact implementation depends on the chosen premixed-combustion closure. Infer and justify plausible turbulence and flame-wrinkling closures from the observations. These closure choices, and thermochemical representations that are observationally indistinguishable over this short transient, are not uniquely identifiable.

The observations describe physical time t = 0.005 s. This is a finite transient numerical state, not an asserted steady or mesh-converged solution. The original setup is one realization capable of producing it, not uniquely identifiable ground truth.

## Deliverable

Submit a successful native calculation with the observed endpoint fields saved at t = 0.005 s. Depending on the supplied observation schema, these may include velocity `U` (m/s), absolute pressure `p` (Pa), temperature `T` and unburnt temperature `Tu` (K), unburnt progress variable `b`, total and auxiliary fuel variables `ft` and `fu`, flame-wrinkling factor `Xi`, laminar flame speed `Su` (m/s), turbulent kinetic energy `k` (m2/s2), dissipation rate `epsilon` (m2/s3), turbulent kinematic viscosity `nut` (m2/s), and turbulent thermal-diffusion coefficient `alphat` (kg/(m s)). Save only fields actually evolved or produced by your physical model; do not synthesize absent fields.

Choose mesh resolution and numerical controls within the execution budget, while retaining the physical coordinates and two-dimensional character of the supplied geometry. Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver name, dictionary recipe, mesh topology or long explanation is required.

The target data may be used for analysis and calibration of physically interpretable material, ignition and closure parameters. Do not initialize or prescribe an internal field from the target endpoint, construct pointwise forcing that pins the interior to target samples, or substitute supplied observations for native output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a copying or restart task.
