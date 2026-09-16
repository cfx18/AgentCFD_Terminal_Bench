# Reconstruct a sphere crossing an air-water interface

You are given the three-dimensional exterior geometry and dense native observations of a moving rigid sphere and two-phase flow. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The fluid region is represented by a 5-degree axisymmetric sector of a vertical cylinder with radius 0.572 m and vertical extent -1 <= y <= 1 m. The sector is centred on the negative x direction, with its two planar faces at azimuths of +/-2.5 degrees. A rigid sphere of radius 0.028 m is centred initially on the cylinder axis at (0, 0.147, 0). The outer cylindrical surface and bottom are stationary no-slip walls, the top is an ambient opening, and the two sector faces represent axisymmetry. The sphere is a moving no-slip boundary constrained to translate only along the vertical axis.

The problem family is laminar, immiscible air-water flow with heat transport, gravity, surface tension, compressible ideal-gas air, constant-density liquid water, and two-way rigid-body coupling. Gravity is (0, -9.81, 0) m/s2 and the air-water surface tension is 0.07 N/m. Water has density 1027 kg/m3, specific heat 4195 J/(kg K), dynamic viscosity 3.645e-4 Pa s, and molecular Prandtl number 2.289. Air has molecular weight 28.9 kg/kmol, specific heat 1007 J/(kg K), dynamic viscosity 1.84e-5 Pa s, and molecular Prandtl number 0.7. No turbulence model, phase change, radiation, or volumetric heat source is present.

Initially, water occupies y <= 0 and air occupies y > 0. Both phases are at rest at 300 K and the initial absolute pressure is 101325 Pa. The sphere starts with vertical velocity (0, -3.77, 0) m/s. Its mass is 2.08e-3 kg for the 5-degree sector force balance, equivalent to approximately 0.14976 kg for the full sphere when forces and mass are scaled consistently. The body orientation is fixed.

Gravity, the initial sphere impulse, wall motion, and the ambient pressure/temperature state are known forcing. The exact numerical treatment of the open top, interface compression, dynamic mesh, rigid-body coupling, and pressure splitting is not supplied; infer and justify a plausible realization. The original configuration is only one discretized realization and is not uniquely identifiable from the observations. In particular, hydrostatic-reduced pressure depends on the chosen pressure convention, and small thermal changes can depend on the compressible energy formulation.

## Deliverable

Compute to physical time t = 0.07 s and submit a successful native calculation with the velocity, water volume fraction, absolute pressure, hydrostatic-reduced pressure, mixture and phase temperatures, and rigid-body position/motion saved at that time. Use SI units and preserve the supplied physical coordinate system. Choose your own mesh resolution, dynamic-mesh strategy, and numerical controls within the execution budget; no particular mesh topology or solver-dictionary recipe is required.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives, and verified results. The target is a finite transient numerical reconstruction, not proof of mesh convergence or a uniquely recovered physical model. Do not treat a successful process exit as evidence of convergence without quantitative checks.

The target data may be used for analysis and calibration, including physically interpretable numerical and coupling parameters. Do not initialize or prescribe the target terminal fields, construct pointwise forcing that pins the interior or sphere trajectory to the target, or substitute target data for native output. Start from the stated physical initial condition and initial body velocity. This is a reconstruction task, not a test of copying or restarting an existing solution.
