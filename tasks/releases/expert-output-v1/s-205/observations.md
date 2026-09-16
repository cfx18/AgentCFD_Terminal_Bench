# Observation definitions

Use the actual native output at t = 0.007 s. Except for boundary fluxes and wall heat integrals, statistics refer to internal cells only. Let V denote the native cell volumes. A volume-weighted mean is sum(V * f) / sum(V), not an arithmetic cell mean. Report all the following keys exactly, with the given units and number of components. This table completely defines the measurement object in the accompanying report protocol.

| Key | Unit | Size | Definition |
|---|---|---:|---|
| final_time | s | 1 | Actual terminal physical time. |
| cell_count | 1 | 1 | Actual number of internal cells. |
| volume | m3 | 1 | Sum of the native internal cell volumes. |
| mass | kg | 1 | Sum of rho * V. |
| axial_momentum | kg m/s | 1 | Sum of rho * Ux * V. |
| total_energy | J | 1 | Sum of (p/(gamma - 1) + rho * (Ux^2 + Uy^2 + Uz^2)/2) * V, with gamma = Cp/(Cp - R). Exclude the formation-enthalpy offset. |
| U_volume_mean | m/s | 3 | Volume-weighted mean of Ux, Uy, Uz, in that order. |
| transverse_velocity_rms | m/s | 1 | Square root of the volume-weighted mean of (Uy^2 + Uz^2). |
| last_initial_residual | 1 | 1 | Initial residual from the last rhoE solve in the final Time block of solver.log. |
| last_final_residual | 1 | 1 | Final residual from the last rhoE solve in the final Time block of solver.log. |
| rho_axial_bin_mean | kg/m3 | 40 | Volume-weighted rho in the 40 fixed axial observation bins defined below, in increasing x order. |
| p_axial_bin_mean | Pa | 40 | Volume-weighted p in the 40 fixed axial observation bins defined below, in increasing x order. |
| T_axial_bin_mean | K | 40 | Volume-weighted T in the 40 fixed axial observation bins defined below, in increasing x order. |
| Ux_axial_bin_mean | m/s | 40 | Volume-weighted Ux in the 40 fixed axial observation bins defined below, in increasing x order. |

## Axial observations and energy

Split [-5, 5] m into 40 equal-width observation bins of 0.25 m, ordered by increasing x. They are not a requirement to use 40 computational cells. Report rho, absolute p, T, and the signed axial velocity Ux.

For the supported one-dimensional mesh, cross-sectional area is 4 m2. Each axial cell width is V/4 and its endpoints are Cx - V/8 and Cx + V/8. Treat the cell value as piecewise constant and weight it by its overlap volume with each observation bin. This definition permits graded axial cells and arbitrary cell storage order.

Use R = 8314.46261815324/28.96 J/(kg K) and gamma = Cp/(Cp - R). The reported total_energy is sensible internal energy plus kinetic energy; do not add the constant formation-enthalpy offset. Do not replace the native waveforms with values from an analytic solution.
