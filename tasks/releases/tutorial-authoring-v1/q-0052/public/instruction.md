# Reconstruct steady diffusion through a thin rectangular slab

You are given the three-dimensional exterior geometry and dense synthetic observations of a temperature-like scalar field. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The connected homogeneous domain is the rectangular slab 0 <= x <= 0.10, 0 <= y <= 0.10 and 0 <= z <= 0.01. It represents a two-dimensional problem extruded through the z thickness: the solution is invariant in z, and the two thickness faces are not physical heat-transfer boundaries. There is no physical internal wall or material interface.

The problem family is steady, source-free scalar diffusion, interpretable as heat conduction with temperature field T. The field has temperature dimensions and the uniform diffusivity is 4e-5 m2/s. No density, heat capacity or conductivity is separately specified, so only the diffusivity is identifiable. There is no advection, fluid motion, volumetric source, radiation, phase change or contact resistance.

Initially T is uniform at 1 K. The exterior thermal boundary forcing is not supplied; infer a plausible realization from the observed field. Distinguish inferred fixed values or fluxes from the known absence of volumetric forcing. The very small 0--1 K scale is part of the numerical reference but is physically ambiguous: it may be read literally in kelvin or as a normalized temperature represented with temperature dimensions.

The observations are a saved steady numerical endpoint with output index 1. Since the governing model is steady, this index is not one second and carries no physical elapsed-time meaning. Boundary conditions inferred from an interior steady field need not be unique. Likewise, small mesh- or interface-scale artifacts in the observations do not establish a physical interface or a unique original discretization; the reference configuration is only one numerical realization.

## Deliverable

Submit a successful native calculation with the final scalar field T saved at a stationary endpoint. Use physical coordinates in the supplied geometry and choose your own mesh, boundary realization, solver and numerical controls. Do not add velocity, pressure or synthetic thermal fields that are absent from this diffusion problem.

Give a short final modeling note separating known information, inferred forcing, unresolved alternatives and verified numerical results. No particular solver, dictionary recipe, mesh topology, iteration count or long explanation is required. Quantitative reconstruction and the observable modeling process are reviewed separately.

The target data may be used for analysis and calibration of physically interpretable boundary parameters. Do not initialize or prescribe the target internal field, construct pointwise or cellwise forcing that pins the interior to the target, copy the target as native output, or encode a volume mesh from the observation points. Start from the stated uniform initial condition. This is a reconstruction task, not a copying or restart task.
