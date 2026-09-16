# Reconstruct coupled heat diffusion across a split slab

You are given the exterior geometry and dense synthetic observations of a temperature field, with physical cell coordinates and cell volumes. Build and run an OpenFOAM v2306 case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The domain is a rectangular slab occupying 0 <= x <= 0.10, 0 <= y <= 0.10 and 0 <= z <= 0.01. It consists of two adjacent regions separated by the plane x = 0.05. The observation represents a two-dimensional problem extruded through the stated thickness; the temperature is uniform through the thickness. The common interface transmits heat between the regions. This geometry description does not prescribe a volume mesh or require matching cell faces across the interface.

The physical family is source-free, isotropic heat diffusion in two stationary homogeneous regions. Both regions have thermal diffusivity 4.0e-5 m2/s. There is no fluid motion, volumetric heat generation, radiation or phase change. Density, heat capacity and thermal conductivity are not separately identifiable from the supplied diffusivity. The outer thermal forcing and the detailed interface realization are not supplied: infer and justify a plausible set of boundary and coupling conditions from the observations. The original configuration is only one numerical realization and is not uniquely identifiable ground truth.

Initially the left region has uniform temperature 1 K and the right region has uniform temperature 0 K. These very small values should be understood as the authored temperature scale for this numerical diffusion problem; they do not establish a realistic absolute-temperature experiment. The observations correspond to terminal numerical label 5. The governing family is steady diffusion, so this label is an iteration/write label rather than five seconds of physical transient evolution.

## Deliverable

Submit a successful native calculation with the temperature field saved at numerical label 5 in both regions. Temperature observations have units K. Choose your own mesh, coupling approach, stopping strategy and numerical controls within the execution budget. Preserve the supplied physical coordinates and the two-region interface, but do not treat the observation cell locations as a required mesh.

Give a short final modeling note separating known information, inferred boundary and interface choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or long explanation is required. Concise decision summaries during work are welcome; reconstruction accuracy does not prove that an inferred forcing or coupling mechanism is unique.

The target data may be used for analysis and calibration, including physically interpretable boundary or interface parameters. Do not initialize or prescribe the target terminal field, construct pointwise or cellwise forcing that pins the interior to the observations, or substitute target data for native output. Start from the stated piecewise-uniform initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
