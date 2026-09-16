# Reconstruct two-dimensional passive-scalar advection

You are given the exterior geometry and dense numerical observations of a velocity field and a dimensionless passive scalar. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The modeled region is the square 0 <= x <= 1 and 0 <= y <= 1, represented by the supplied extrusion over 0 <= z <= 0.1. The problem is two-dimensional: the two thickness faces are empty planes, not physical walls. The remaining four sides are open boundaries. The exterior file describes geometry only and does not prescribe a volume mesh.

This is pure transport of a dimensionless passive scalar, stored as field `T`; it is not temperature. The velocity is prescribed and spatially uniform at (1, 1, 0) m/s, and the scalar diffusivity is zero. There is no momentum or pressure solve, material density, heat transfer, reaction, source term, gravity, turbulence, or phase change.

Initially the internal scalar is uniform at 1e-8. The prescribed flow enters through the left and bottom sides and leaves through the top and right sides. The scalar entering from the left is 1, while that entering from the bottom is 0. These physical velocity and inflow values are known. The exact numerical treatment of the outflow, mesh, convective flux, and time integration is not supplied; choose a defensible realization and describe it as inferred rather than uniquely recovered.

Compute from t = 0 to physical time t = 100 s. The supplied observations describe the terminal numerical state. The transit time across the domain is much shorter than the observation time, but this does not by itself certify numerical stationarity or conservation.

## Deliverable

Submit a successful native calculation with the velocity `U` in m/s and dimensionless scalar `T` saved at t = 100 s. Use the physical coordinates in the supplied geometry and generate your own mesh. No pressure or temperature field is requested.

Give a short final modeling note separating known information, inferred numerical and boundary choices, unresolved alternatives, and verified results. No particular solver, dictionary recipe, mesh resolution, or reasoning sequence is required. The archived configuration that generated the observations is only one numerical realization; agreement with it does not uniquely identify a ground-truth discretization.

The target data may be used for analysis and calibration, including physically interpretable boundary parameters and numerical choices. Do not initialize or prescribe the interior from the target terminal field, construct pointwise forcing that pins cells to the observations, or substitute target data for native output. Start from the stated uniform initial scalar. This is a reconstruction task, not a copying or restart task.
