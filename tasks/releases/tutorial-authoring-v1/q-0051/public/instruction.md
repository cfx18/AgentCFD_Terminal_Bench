# Reconstruct transient heat diffusion in a three-dimensional solid

You are given the exterior geometry and dense synthetic observations of temperature inside a connected three-dimensional solid. Build and run an OpenFOAM v2306 case that reproduces the observations. Generate your own volume mesh and case inputs; the supplied surface is geometry only and does not prescribe a volume mesh. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The solid is bounded by approximately -0.0260093 <= x <= 0.0260093, -0.0275 <= y <= 0.0225, and -0.02375 <= z <= 0.00225014. Use `/input/geometry/domain.stl` as the authoritative exterior shape. Surface-region names in that file are neutral geometry labels and do not prescribe thermal boundary conditions.

The problem family is transient heat diffusion in a stationary, homogeneous, isotropic solid with constant thermal diffusivity 4e-5 m2/s. There is no fluid motion, volumetric heat source, radiation, phase change, or moving geometry. A material identity, density, heat capacity, and conductivity are not separately specified; only their diffusivity ratio is known.

Initially the entire solid is at 273 K. Heating or cooling can occur only through the exterior boundary. The locations, types, values, and histories of the thermal boundary forcing are not supplied: infer and justify a plausible realization from the geometry and observations. Different boundary descriptions can be observationally indistinguishable at one time, so do not claim unique recovery of forcing that the data cannot identify.

Compute from the stated initial condition to physical time t = 3 s. The observations describe this terminal transient state; they are not evidence that the solid has reached steady state.

## Deliverable

Submit a successful native calculation with the temperature field saved at t = 3 s in kelvin. Choose the mesh and numerical controls within the execution budget, and retain the supplied physical coordinate system. No velocity or pressure field is requested.

Give a short final modeling note separating known information, inferred boundary forcing, unresolved alternatives, and verified results. No particular reasoning sequence, solver name, dictionary recipe, or configuration template is required. Concise decision summaries during work are welcome; quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration of physically interpretable boundary parameters. Do not initialize the interior from the target field, prescribe target values point by point, add an interior forcing that pins the solution to the observations, or substitute target data for native output. Start from the stated uniform 273 K condition. The hidden reference configuration is one realization, not uniquely identifiable ground truth.
