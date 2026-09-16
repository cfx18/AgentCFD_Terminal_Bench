# Reconstruct a rarefied binary-gas free stream in an open box

You are given the three-dimensional exterior geometry and dense synthetic observations of a dilute molecular-gas state. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The observed region is the rectangular box
-0.05 <= x <= 0.05, -0.04 <= y <= 0.04 and -0.04 <= z <= 0.04. All six faces are open to the same unbounded gas reservoir; there are no solid walls or internal obstacles.

The problem family is a transient direct-simulation Monte Carlo description of a non-reacting, rarefied N2/O2 mixture. Number fractions are 0.777 N2 and 0.223 O2, and the total number density is 1.0e20 m^-3. The molecular data are:

- N2: molecular mass 46.5e-27 kg, reference diameter 4.17e-10 m, two internal degrees of freedom, and variable-hard-sphere viscosity exponent 0.74.
- O2: molecular mass 53.12e-27 kg, reference diameter 4.07e-10 m, two internal degrees of freedom, and variable-hard-sphere viscosity exponent 0.77.

Initially the gas is spatially uniform at 300 K with bulk velocity (1325, -352, 823) m/s and the species number densities stated above. The far-field reservoir has the same composition, number density, temperature and bulk velocity. There is no gravity, chemistry, volumetric source, imposed pressure gradient, moving boundary or wall heat transfer.

The molecular collision/energy-redistribution implementation, simulation-particle weight, random seed, mesh and open-boundary parcel-injection details are not prescribed. Infer and justify a plausible kinetic realization. A variable-hard-sphere collision family with rotational energy exchange is consistent with the known material data, but the terminal observations do not uniquely identify every closure or numerical parameter.

Compute to physical time t = 0.02 s. The observations describe only this terminal state and contain finite-sampling noise from one stochastic numerical realization. Reproduce the resolved physical statistics rather than claiming that random cellwise fluctuations uniquely determine the hidden realization.

## Deliverable

Submit a successful native calculation with the terminal species-total number density (m^-3), mass density (kg/m3), bulk velocity (m/s), momentum density (kg/(m2 s)), translational kinetic-energy density (J/m3), internal-energy density (J/m3), internal-degree-of-freedom density (m^-3), and translational, internal and overall temperatures (K) saved at t = 0.02 s wherever your formulation provides them. Preserve any time-averaged native fields used for comparison. Choose the volume mesh, particle weight and numerical controls within the execution budget; the final fields must use the physical coordinates of the supplied geometry.

Give a short final modeling note separating known information, inferred choices, stochastic uncertainty and verified results. The original setup is one realization, not uniquely identifiable ground truth. No particular solver name, dictionary layout, mesh topology or long explanation is required.

The target data may be used for analysis and calibration, including physically interpretable kinetic and boundary parameters. Do not initialize or prescribe the target terminal field, construct cellwise or pointwise forcing that pins the interior to the observations, or substitute target data for native output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
