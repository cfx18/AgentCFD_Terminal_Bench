# Observation definitions

Use the actual native output at t = 1.5 s. Except for boundary fluxes and wall heat integrals, statistics refer to internal cells only. Let V denote the native cell volumes. A volume-weighted mean is sum(V * f) / sum(V), not an arithmetic cell mean. Report all the following keys exactly, with the given units and number of components. This table completely defines the measurement object in the accompanying report protocol.

| Key | Unit | Size | Definition |
|---|---|---:|---|
| final_time | s | 1 | Actual terminal physical time. |
| pressure_initial_residual | 1 | 1 | Initial residual from the last p solve in the final Time block of solver.log. |
| pressure_final_residual | 1 | 1 | Final residual from the last p solve in the final Time block of solver.log. |
| cell_count | 1 | 1 | Actual number of internal cells. |
| volume | m3 | 1 | Sum of the native internal cell volumes. |
| T_volume_mean | K | 1 | Volume-weighted mean temperature. |
| T_min_max | K | 2 | Minimum and maximum internal temperature, in that order. |
| T_rise_rms | K | 1 | Volume-weighted RMS of (T - 300 K), not the RMS of absolute T. |
| relative_300K_sensible_enthalpy | J | 1 | Sum of rho * Cp * (T - 300 K) * V, using rho = 1.2 kg/m3 and Cp = 1000 J/(kg K). |
| U_volume_mean | m/s | 3 | Volume-weighted mean of Ux, Uy, Uz, in that order. |
| speed_volume_rms | m/s | 1 | Square root of the volume-weighted mean of (Ux^2 + Uy^2 + Uz^2). |
| inlet_flow | m3/s | 1 | Signed sum of the native face volumetric flux on inlet. Positive is outward from this region. |
| inlet_enthalpy_flux | W | 1 | Signed sensible-enthalpy outflow through inlet, relative to 300 K; use native face flux and boundary-face T, as defined below. |
| outlet1_flow | m3/s | 1 | Signed sum of the native face volumetric flux on outlet1. Positive is outward from this region. |
| outlet1_enthalpy_flux | W | 1 | Signed sensible-enthalpy outflow through outlet1, relative to 300 K; use native face flux and boundary-face T, as defined below. |
| outlet2_flow | m3/s | 1 | Signed sum of the native face volumetric flux on outlet2. Positive is outward from this region. |
| outlet2_enthalpy_flux | W | 1 | Signed sensible-enthalpy outflow through outlet2, relative to 300 K; use native face flux and boundary-face T, as defined below. |
| temperature_excess_315K | K | 1 | Volume-weighted mean of (T - 315 K); keep its sign. |

## Flow, heating, and storage

For an opening, phi_f is the signed outward native volumetric face flux in m3/s. Its enthalpy flux is sum(1.2 * phi_f * 1000 * (T_f - 300 K)), including any reverse-flow faces. Use boundary-face temperatures, not the cell-mean temperature multiplied by net flow.

The sensible-enthalpy inventory is referenced to 300 K. The separate temperature_excess_315K measures the volume-mean difference from the inlet temperature; it can be negative and is not an absolute-temperature relative error. These final-state quantities do not by themselves prove a complete transient energy balance.
