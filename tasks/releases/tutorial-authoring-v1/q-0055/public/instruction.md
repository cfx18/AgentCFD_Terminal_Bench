# Reconstruct transient heat diffusion around a translating insulated inclusion

You are given the physical geometry and dense synthetic observations of temperature at the terminal time. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult the provided general documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The problem is planar in the x-y plane, represented over 0 <= z <= 1 with empty front and back boundaries. The exterior region is the square 0 <= x <= 1, 0 <= y <= 1. At t = 0, an internal square exclusion occupies 0.4 <= x <= 0.6 and 0.4 <= y <= 0.6. At the observation time it occupies 0.6 <= x <= 0.8 and 0.4 <= y <= 0.6. The outer geometry and the moving internal boundary are supplied; any overlapping-grid interfaces in the observations are numerical rather than additional physical walls.

The problem family is transient scalar heat diffusion in a homogeneous medium with constant effective thermal diffusivity 1 m2/s. Temperature is measured in kelvin. There is no fluid velocity, volumetric heat source, radiation or phase change. The top and bottom exterior boundaries and the moving internal square are thermally insulating. Density, heat capacity and conductivity are not separately identified by this effective-diffusivity model.

Initially the medium is uniformly at 273 K. The thermal conditions on the left and right exterior boundaries, and the trajectory of the internal square between its stated initial and terminal positions, are not supplied: infer and justify a plausible realization using the observations. The terminal position alone does not uniquely determine the motion history.

The observations describe physical time t = 1 s. They are one finite numerical realization of this moving-domain diffusion problem, not a uniquely identifiable continuum ground truth. Boundary histories, mesh motion and numerical coupling choices can produce closely similar terminal fields, so do not claim to have uniquely recovered mechanisms that the data cannot distinguish.

## Deliverable

Submit a successful native calculation with temperature saved at t = 1 s in kelvin. Build your own mesh and retain the supplied physical coordinates and physical boundaries. Choose mesh resolution, moving-domain treatment and numerical controls within the execution budget.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or configuration template is required. Concise decision summaries during work are welcome; quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration, including physically interpretable boundary temperatures and motion parameters. Do not use the target internal temperature as your initialized or prescribed solution, construct a pointwise source that pins the interior to the target, or substitute target data for native output. Start from the stated uniform initial condition. This is a reconstruction task, not a test of copying or restarting an existing solution.
