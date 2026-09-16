# Observation definitions

Use the actual native output at the actual final iteration. Except for boundary fluxes and wall heat integrals, statistics refer to internal cells only. Let V denote the native cell volumes. A volume-weighted mean is sum(V * f) / sum(V), not an arithmetic cell mean. Report all the following keys exactly, with the given units and number of components. This table completely defines the measurement object in the accompanying report protocol.

| Key | Unit | Size | Definition |
|---|---|---:|---|
| final_iteration | 1 | 1 | Actual last SIMPLE iteration index; not physical time in seconds. |
| cell_count | 1 | 1 | Actual number of internal cells. |
| volume | m3 | 1 | Sum of the native internal cell volumes. |
| mass | kg | 1 | Sum of p * V / (R * T), using local absolute p and T. |
| T_volume_mean | K | 1 | Volume-weighted mean temperature. |
| p_volume_mean | Pa | 1 | Volume-weighted mean absolute pressure. |
| speed_volume_rms | m/s | 1 | Square root of the volume-weighted mean of (Ux^2 + Uy^2 + Uz^2). |
| U_volume_mean | m/s | 3 | Volume-weighted mean of Ux, Uy, Uz, in that order. |
| last_initial_residual | 1 | 1 | Initial residual from the last p_rgh solve in the final Time block of solver.log. |
| last_final_residual | 1 | 1 | Final residual from the last p_rgh solve in the final Time block of solver.log. |
| p_rgh_final_initial_residual | 1 | 1 | Initial residual from the last p_rgh solve in the final iteration. |
| h_final_initial_residual | 1 | 1 | Initial residual from the last h solve in the final iteration. |
| T_last_write_relative_change | 1 | 1 | Volume-weighted mean absolute T change from the preceding saved positive iteration to the final iterate, divided by 19.6 K. |
| U_last_write_relative_change | 1 | 1 | Volume-weighted RMS of the velocity-vector difference between those two writes, divided by final speed_volume_rms (denominator floor 1e-12 m/s). |
| cold_wall_heat_rate | W | 1 | Native area integral of wallHeatFlux on cold. Positive means heat entering the fluid; sum both walls for a grouped patch. |
| frontAndBack_wall_heat_rate | W | 1 | Native area integral of wallHeatFlux on frontAndBack. Positive means heat entering the fluid; sum both walls for a grouped patch. |
| hot_wall_heat_rate | W | 1 | Native area integral of wallHeatFlux on hot. Positive means heat entering the fluid; sum both walls for a grouped patch. |
| topAndBottom_wall_heat_rate | W | 1 | Native area integral of wallHeatFlux on topAndBottom. Positive means heat entering the fluid; sum both walls for a grouped patch. |
| k_volume_mean | m2/s2 | 1 | Volume-weighted mean turbulent kinetic energy. |
| omega_volume_mean | 1/s | 1 | Volume-weighted mean specific dissipation rate. |
| nut_volume_mean | m2/s | 1 | Volume-weighted mean turbulent kinematic viscosity. |
| alphat_volume_mean | kg/(m s) | 1 | Volume-weighted mean compressible turbulent thermal diffusivity as stored natively. |
| T_x_bin_mean | K | 20 | Volume-weighted T in the 20 fixed x observation bins defined below, in increasing coordinate order. |
| Uy_x_bin_mean | m/s | 20 | Volume-weighted Uy in the 20 fixed x observation bins defined below, in increasing coordinate order. |
| T_y_bin_mean | K | 20 | Volume-weighted T in the 20 fixed y observation bins defined below, in increasing coordinate order. |
| Uy_y_bin_mean | m/s | 20 | Volume-weighted Uy in the 20 fixed y observation bins defined below, in increasing coordinate order. |

## Profile bins and stationarity

For the x profiles, split [0, 0.076] m into 20 equal-width bins. For the y profiles, split [0, 2.18] m into 20 equal-width bins. A bin spans the whole cross-section perpendicular to its axis. Report temperature and the vertical velocity component Uy, not velocity magnitude. These are observation bins, not prescribed computational cells.

Treat each native internal field value as constant within its cell. Weight a cell crossing an observation-bin boundary by its geometric overlap volume, not by assigning its entire volume to the bin containing its centre. Report bins in increasing coordinate order, independent of cell storage order.

The stationarity measurements compare the actual final fields with the latest preceding positive-iteration U/T output on the same mesh. Preserve the iteration indices in the returned artifacts. A small difference between closely spaced writes is not by itself evidence that the whole steady problem is converged.

## Pressure and heat

Use absolute thermodynamic pressure in mass and pressure statistics, with R = 8314.46261815324/28.96 J/(kg K). Do not subtract each field's own mean pressure.

The native wallHeatFlux sign is positive into the fluid. Integrate heat-flux density over face area to obtain W; do not sum values in W/m2 without their areas. The hot and cold values refer to the individual temperature-controlled walls. frontAndBack and topAndBottom each sum the two walls in that group. Residuals reported here describe the last corresponding linear solve, not a proof of outer-iteration convergence.
