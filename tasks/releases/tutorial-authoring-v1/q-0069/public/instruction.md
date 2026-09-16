# Reconstruct methane–air autoignition in a homogeneous reactor

You are given the control-volume geometry and thermochemical observations from a transient reacting-gas calculation. Build and run an OpenFOAM v2306 case that reproduces the observations. Generate your own minimal volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

The physical system is a spatially homogeneous, perfectly mixed batch reactor. It has no resolved inlets, outlets or spatial gradients; the supplied geometry is only a finite-volume representation of the well-mixed control volume and does not define a transport length scale. There is no imposed flow, gravity, radiation, phase change or wall heat transfer.

The gas is an ideal reacting methane–air mixture using detailed GRI-Mech 3.0 chemistry (53 species and 325 reactions) with temperature-dependent JANAF thermodynamics and sensible enthalpy as the energy variable. The reactor pressure is held at 1.36789e6 Pa. This pressure constraint is known forcing; there is no boundary forcing. The detailed numerical chemistry integration controls and the physically irrelevant realization of the bookkeeping control volume are not supplied and may be inferred from the observations.

Initially, at t = 0 s, the mixture is at 1000 K. Its mole proportions are CH4:O2:N2 = 0.5:1:3.76, corresponding to mole fractions 0.0950570342, 0.1901140684 and 0.7148288973. All other mechanism species initially have zero abundance. This is a stoichiometric methane–air mixture. Start from this uniform physical state and evolve it to t = 0.07 s.

The observations describe one finite numerical realization of the homogeneous ignition transient. They do not uniquely determine integration tolerances, chemistry time-step controls, thermodynamic-library details, or other numerically equivalent choices. Do not claim to have uniquely recovered choices that the data cannot distinguish.

## Deliverable

Submit a successful native calculation with temperature, absolute pressure, density and all available species mass fractions saved at t = 0.07 s. Preserve the physical coordinate system supplied with the observations, while recognizing that a homogeneous reactor has only one independent thermochemical state. Use SI units: temperature in K, pressure in Pa, density in kg/m3 and mass fractions dimensionless.

Give a short final modeling note separating known information, inferred numerical choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or long explanation is required. Report quantitative conservation and endpoint checks; completion of a process alone is not evidence of numerical or physical consistency.

The target data may be used for analysis and calibration, including physically interpretable kinetic or thermodynamic choices. Do not initialize or prescribe the reactor from the target terminal fields, impose a time-dependent or pointwise source that pins the state to the target, or substitute target data for native output. Begin from the stated 1000 K methane–air mixture. This is a reconstruction task, not a copying or restart task.
