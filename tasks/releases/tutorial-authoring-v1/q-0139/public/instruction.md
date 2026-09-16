# Reconstruct transient magnetohydrodynamic channel flow

You are given the three-dimensional exterior geometry and dense synthetic observations of velocity, magnetic induction, kinematic pressure and the magnetic divergence-control scalar. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult the provided general documentation and source code.

## Known physical information

Coordinates are in metres. The fluid region is a rectangular channel occupying 0 <= x <= 20, -1 <= y <= 1 and 0 <= z <= 0.1. The planes at x = 0 and x = 20 are openings. The planes at y = -1 and y = 1 are stationary, impermeable, no-slip walls. This is a planar two-dimensional model: the z = 0 and z = 0.1 faces represent the empty-direction extrusion, not physical walls. The neutral surface geometry does not prescribe a volume mesh or boundary names.

The problem family is transient, laminar, incompressible resistive magnetohydrodynamics for a Newtonian electrically conducting fluid. Density is 1 kg/m3, kinematic viscosity is 1 m2/s, magnetic permeability is 1 H/m and electrical conductivity is 1 S/m; the corresponding magnetic diffusivity is 1 m2/s. There is no temperature field, compressibility, turbulence model, gravity, phase change or moving wall.

Initially the fluid is at rest, the magnetic induction is uniform at (0, 20, 0) T, and both kinematic pressure and the magnetic divergence-control scalar are zero. No independent volumetric mechanical forcing is known. The flow and magnetic boundary forcing at the two openings and walls, the pressure references, and the detailed driving history are not supplied: infer and justify a plausible realization from the observations. Different boundary descriptions can generate nearly indistinguishable finite-time interior states, so do not claim that these choices are uniquely identified.

Compute to physical time t = 2 s. The supplied observations describe only that terminal time. They are one finite numerical realization, not a uniquely identifiable continuum ground truth or proof of steady convergence.

## Deliverable

Submit a successful native calculation with velocity `U` in m/s, magnetic induction `B` in tesla, kinematic pressure `p` in m2/s2, and the magnetic divergence-control field `pB` in V/m saved at t = 2 s. The latter has dimensions of magnetic induction times velocity, [1 1 -3 0 0 -1 0]. Generate your own mesh, use the physical coordinates in the supplied geometry, and retain the planar empty direction. Do not create or report a temperature field.

Give a short final modeling note separating known information, inferred forcing, unresolved alternatives and verified numerical results. No particular solver name, dictionary recipe, configuration template or long explanation is required. Concise decision summaries during work are welcome; reconstruction accuracy and physical interpretation are assessed separately.

The target data may be used for analysis and calibration, including physically interpretable boundary and material parameters. Do not use any target internal field as an initialized or prescribed solution, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
