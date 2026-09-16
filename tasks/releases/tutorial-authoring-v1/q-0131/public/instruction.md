# Reconstruct a periodic rarefied-gas mixture

You are given the exterior geometry and dense statistical observations of a freely moving rarefied-gas mixture. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are Cartesian and in metres. The domain is the rectangular box -0.05 <= x <= 0.05, -0.04 <= y <= 0.04 and -0.04 <= z <= 0.04. Each pair of opposite faces is translationally periodic. There are no physical walls, openings, inflows, moving boundaries or external body forces, and there is no imposed heat source.

The physical family is a three-dimensional direct-simulation Monte Carlo model of a binary nitrogen/oxygen mixture. Initially, the N2 and O2 number densities are respectively 0.777e20 and 0.223e20 molecules/m3, the temperature is 300 K, and the bulk velocity is (1950, 0, 0) m/s. N2 has molecular mass 46.5e-27 kg, reference collision diameter 4.17e-10 m, two internal degrees of freedom and viscosity index 0.74. O2 has molecular mass 53.12e-27 kg, reference collision diameter 4.07e-10 m, two internal degrees of freedom and viscosity index 0.77. Use a variable-hard-sphere binary-collision family with Larsen-Borgnakke translational/internal energy redistribution; the reference temperature is 273 K and the rotational relaxation collision number is 5.

The observations are the terminal cumulative statistical state at physical time t = 1.0e-3 s, averaged from the initial time. They include mean velocity, translational, internal and overall temperature, pressure, mean number and mass density, mean momentum density, mean translational kinetic- and internal-energy density, and mean internal-degree-of-freedom density. Pressure is in Pa and the temperature values are in K. The metadata preserves a native dimension-vector inconsistency on the three temperature files; interpret those quantities physically as temperature. A mean DSMC parcel population per cell is included only as a sampling diagnostic and is not a mesh-independent physical target.

The absence of physical forcing is known. Parcel weight and count, random realization, collision sampling, volume mesh, timestep and statistical implementation are not uniquely determined by the observations and should be chosen or inferred. The supplied data are one finite stochastic realization, not a unique ground truth for those numerical choices. Exact pointwise agreement below the sampling uncertainty is neither physically identifiable nor expected.

## Deliverable

Submit a successful native calculation through t = 1.0e-3 s with the corresponding physical statistical fields saved at that time. Use the supplied exterior surface only as geometry and generate your own volume mesh. Compare on the supplied physical cell-centre coordinates; the listed native cell volumes provide integration weights but do not prescribe your mesh.

Give a short final modeling note separating known physical information, inferred numerical/statistical choices, unresolved alternatives and verified results. No particular solver dictionary, mesh resolution, solver name or long explanation is required.

The target data may be used for analysis and calibration of physically interpretable parameters and statistical controls. Do not initialize or prescribe the target internal fields, construct pointwise forcing that pins the interior to the observations, or substitute supplied target values for native output. Start from the stated uniform macroscopic initial condition and generate the particle realization independently. This is a reconstruction task, not a test of copying or restarting an existing solution.
