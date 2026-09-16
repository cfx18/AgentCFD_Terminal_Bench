# Reconstruct a plane-stress cantilever under end traction

You are given the exterior geometry and cellwise numerical observations of displacement and a pressure-dimensional solid-stress scalar. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The beam cross-section occupies 0 <= x <= 30 and 0 <= y <= 1. The supplied geometry has a unit reference thickness, 0 <= z <= 1, but the physical family is a two-dimensional plane-stress idealization rather than a fully three-dimensional constrained solid. The end at x = 0 is clamped. The long surfaces at y = 0 and y = 1 are traction-free.

The body is homogeneous, isotropic and linearly elastic, with Young's modulus 2.0e11 Pa, Poisson ratio 0, and density 7854 kg/m3. Thermal stress is absent; there is no temperature field to reconstruct. No body force is present.

The applied forcing is known: the end at x = 30 has a uniform surface traction (0, 10000, 0) Pa and zero applied normal pressure. There are no inferred load parameters. Mesh resolution, numerical controls, and the precise implementation of the plane-stress constitutive relation are modeling choices to infer and justify from the observations.

The initial numerical state has zero displacement and zero solid-pressure scalar everywhere. The requested observation is a static equilibrium state. Its native terminal label is 5000, but this is an iteration or pseudo-time label, not 5000 seconds and not a measured physical duration.

The scalar pressure observation is measured in Pa and belongs to the solid-stress formulation; it is not fluid pressure. Different mathematically consistent stress-variable formulations may not expose an identical auxiliary scalar, so explain how your reported scalar corresponds to the observed quantity. The unit-thickness representation, coarse reference discretization, and auxiliary stress-variable convention are potential ambiguities. The observations describe one numerical realization and do not uniquely identify a ground-truth mesh or algorithm.

## Deliverable

Submit a successful native static calculation with displacement in metres and the pressure-dimensional solid-stress scalar in pascals saved at the equilibrium endpoint. Build your own mesh in the supplied physical coordinates. Give a short final modeling note separating known information, inferred numerical choices, unresolved alternatives and verified equilibrium evidence. No particular solver, dictionary recipe, mesh topology or long explanation is required.

The target data may be used for analysis and calibration of physically interpretable choices. Do not initialize or prescribe the target displacement or stress field, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated zero initial state. This is a reconstruction task, not a test of copying or restarting an existing solution.
