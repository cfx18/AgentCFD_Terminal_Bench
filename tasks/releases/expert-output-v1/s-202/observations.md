# Observation definitions

Use the actual native output at t = 100 s. Except for boundary fluxes and wall heat integrals, statistics refer to internal cells only. Let V denote the native cell volumes. A volume-weighted mean is sum(V * f) / sum(V), not an arithmetic cell mean. Report all the following keys exactly, with the given units and number of components. This table completely defines the measurement object in the accompanying report protocol.

| Key | Unit | Size | Definition |
|---|---|---:|---|
| final_time | s | 1 | Actual terminal physical time. |
| pressure_initial_residual | 1 | 1 | Initial residual from the last p_rgh solve across both fluid regions in the final Time block of solver.log. |
| pressure_final_residual | 1 | 1 | Final residual from the last p_rgh solve across both fluid regions in the final Time block of solver.log. |
| bottomWater_cell_count | 1 | 1 | Region bottomWater: Actual number of internal cells. |
| bottomWater_volume | m3 | 1 | Region bottomWater: Sum of the native internal cell volumes. |
| bottomWater_T_volume_mean | K | 1 | Region bottomWater: Volume-weighted mean temperature. |
| bottomWater_T_min_max | K | 2 | Region bottomWater: Minimum and maximum internal temperature, in that order. |
| bottomWater_T_rise_rms | K | 1 | Region bottomWater: Volume-weighted RMS of (T - 300 K), not the RMS of absolute T. |
| bottomWater_relative_300K_sensible_enthalpy | J | 1 | Region bottomWater: Sum of rho * Cp * (T - 300 K) * V in this region. Use local ideal-gas density for air, constant material density otherwise. |
| bottomWater_U_volume_mean | m/s | 3 | Region bottomWater: Volume-weighted mean of Ux, Uy, Uz, in that order. |
| bottomWater_speed_volume_rms | m/s | 1 | Region bottomWater: Square root of the volume-weighted mean of (Ux^2 + Uy^2 + Uz^2). |
| bottomWater_minX_flow | kg/s | 1 | Region bottomWater: Signed sum of the native face mass flux on minX. Positive is outward from this region. |
| bottomWater_minX_enthalpy_flux | W | 1 | Region bottomWater: Signed sensible-enthalpy outflow through minX, relative to 300 K; use native face flux and boundary-face T, as defined below. |
| bottomWater_maxX_flow | kg/s | 1 | Region bottomWater: Signed sum of the native face mass flux on maxX. Positive is outward from this region. |
| bottomWater_maxX_enthalpy_flux | W | 1 | Region bottomWater: Signed sensible-enthalpy outflow through maxX, relative to 300 K; use native face flux and boundary-face T, as defined below. |
| topAir_cell_count | 1 | 1 | Region topAir: Actual number of internal cells. |
| topAir_volume | m3 | 1 | Region topAir: Sum of the native internal cell volumes. |
| topAir_T_volume_mean | K | 1 | Region topAir: Volume-weighted mean temperature. |
| topAir_T_min_max | K | 2 | Region topAir: Minimum and maximum internal temperature, in that order. |
| topAir_T_rise_rms | K | 1 | Region topAir: Volume-weighted RMS of (T - 300 K), not the RMS of absolute T. |
| topAir_relative_300K_sensible_enthalpy | J | 1 | Region topAir: Sum of rho * Cp * (T - 300 K) * V in this region. Use local ideal-gas density for air, constant material density otherwise. |
| topAir_U_volume_mean | m/s | 3 | Region topAir: Volume-weighted mean of Ux, Uy, Uz, in that order. |
| topAir_speed_volume_rms | m/s | 1 | Region topAir: Square root of the volume-weighted mean of (Ux^2 + Uy^2 + Uz^2). |
| topAir_minX_flow | kg/s | 1 | Region topAir: Signed sum of the native face mass flux on minX. Positive is outward from this region. |
| topAir_minX_enthalpy_flux | W | 1 | Region topAir: Signed sensible-enthalpy outflow through minX, relative to 300 K; use native face flux and boundary-face T, as defined below. |
| topAir_maxX_flow | kg/s | 1 | Region topAir: Signed sum of the native face mass flux on maxX. Positive is outward from this region. |
| topAir_maxX_enthalpy_flux | W | 1 | Region topAir: Signed sensible-enthalpy outflow through maxX, relative to 300 K; use native face flux and boundary-face T, as defined below. |
| heater_cell_count | 1 | 1 | Region heater: Actual number of internal cells. |
| heater_volume | m3 | 1 | Region heater: Sum of the native internal cell volumes. |
| heater_T_volume_mean | K | 1 | Region heater: Volume-weighted mean temperature. |
| heater_T_min_max | K | 2 | Region heater: Minimum and maximum internal temperature, in that order. |
| heater_T_rise_rms | K | 1 | Region heater: Volume-weighted RMS of (T - 300 K), not the RMS of absolute T. |
| heater_relative_300K_sensible_enthalpy | J | 1 | Region heater: Sum of rho * Cp * (T - 300 K) * V in this region. Use local ideal-gas density for air, constant material density otherwise. |
| leftSolid_cell_count | 1 | 1 | Region leftSolid: Actual number of internal cells. |
| leftSolid_volume | m3 | 1 | Region leftSolid: Sum of the native internal cell volumes. |
| leftSolid_T_volume_mean | K | 1 | Region leftSolid: Volume-weighted mean temperature. |
| leftSolid_T_min_max | K | 2 | Region leftSolid: Minimum and maximum internal temperature, in that order. |
| leftSolid_T_rise_rms | K | 1 | Region leftSolid: Volume-weighted RMS of (T - 300 K), not the RMS of absolute T. |
| leftSolid_relative_300K_sensible_enthalpy | J | 1 | Region leftSolid: Sum of rho * Cp * (T - 300 K) * V in this region. Use local ideal-gas density for air, constant material density otherwise. |
| rightSolid_cell_count | 1 | 1 | Region rightSolid: Actual number of internal cells. |
| rightSolid_volume | m3 | 1 | Region rightSolid: Sum of the native internal cell volumes. |
| rightSolid_T_volume_mean | K | 1 | Region rightSolid: Volume-weighted mean temperature. |
| rightSolid_T_min_max | K | 2 | Region rightSolid: Minimum and maximum internal temperature, in that order. |
| rightSolid_T_rise_rms | K | 1 | Region rightSolid: Volume-weighted RMS of (T - 300 K), not the RMS of absolute T. |
| rightSolid_relative_300K_sensible_enthalpy | J | 1 | Region rightSolid: Sum of rho * Cp * (T - 300 K) * V in this region. Use local ideal-gas density for air, constant material density otherwise. |

## Fluxes and thermal storage

All region-prefixed quantities use cells from that named region only. For a fluid opening, let phi_f be the outward mass flux of each face in kg/s. The reported enthalpy flux is sum(phi_f * Cp * (T_f - 300 K)); it includes reverse-flow faces with their actual sign. Use Cp = 4181 J/(kg K) for water and 1000 J/(kg K) for air.

For volume storage, use water density 1000 kg/m3, each solid density 8000 kg/m3, and local air density p/(R T), where R = 8314.46261815324/28.9 J/(kg K). Use the corresponding material heat capacities. These reported sensible-enthalpy inventories and opening enthalpy fluxes are not, on their own, a complete transient energy balance: storage rates, conduction, kinetic energy, and applicable pressure/gravity terms are separate native diagnostics. Do not infer zero transient storage or zero compressible mass storage from a single final snapshot.

Keep native contact and exterior wall-heat fields/logs when the service returns them; they are inspected independently and are not extra measurement keys in this schema.
