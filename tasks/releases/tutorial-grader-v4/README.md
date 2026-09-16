# Tutorial dense-observation grader release

This release contains executable metric-grader policies generated from completed authoring evidence.
A task with `release_status: review` or `blocked` must not be used as a clean leaderboard item.

| task | status | metric grader executable | scored fields | blockers |
|---|---:|---:|---|---:|
| q-0046 | blocked | no | — | 5 |
| q-0050 | blocked | no | — | 6 |
| q-0051 | review | yes | T | 1 |
| q-0052 | blocked | no | — | 4 |
| q-0053 | blocked | no | — | 5 |
| q-0054 | blocked | no | — | 6 |
| q-0055 | blocked | no | — | 4 |
| q-0056 | blocked | no | — | 4 |
| q-0057 | blocked | no | — | 6 |
| q-0058 | blocked | no | — | 5 |
| q-0060 | blocked | no | — | 5 |
| q-0061 | blocked | no | — | 5 |
| q-0062 | blocked | no | — | 5 |
| q-0063 | blocked | no | — | 5 |
| q-0064 | review | yes | T, U, b, ft, p, rho | 3 |
| q-0065 | blocked | no | — | 5 |
| q-0066 | blocked | no | — | 5 |
| q-0068 | blocked | no | — | 5 |
| q-0069 | blocked | no | — | 4 |
| q-0070 | blocked | no | — | 5 |
| q-0071 | blocked | no | — | 6 |
| q-0072 | blocked | no | — | 6 |
| q-0073 | blocked | no | — | 6 |
| q-0074 | blocked | no | — | 4 |
| q-0091 | blocked | no | — | 6 |
| q-0092 | blocked | no | — | 5 |
| q-0094 | review | yes | T_K, U, p_Pa | 1 |
| q-0096 | blocked | no | — | 6 |
| q-0097 | blocked | no | — | 5 |
| q-0098 | blocked | no | — | 4 |
| q-0099 | blocked | no | — | 5 |
| q-0100 | blocked | no | — | 5 |
| q-0101 | blocked | no | — | 5 |
| q-0102 | blocked | no | — | 5 |
| q-0103 | blocked | no | — | 5 |
| q-0104 | blocked | no | — | 6 |
| q-0131 | review | yes | UMean, dsmcRhoNMean, iDofMean, internalEMean, internalT, linearKEMean, momentumMean_x, momentumMean_y, momentumMean_z, overallT, p, rhoMMean, rhoNMean, translationalT | 1 |
| q-0132 | blocked | no | — | 5 |
| q-0133 | blocked | no | — | 6 |
| q-0134 | blocked | no | — | 4 |
| q-0135 | blocked | no | — | 5 |
| q-0136 | blocked | no | — | 5 |
| q-0137 | blocked | no | — | 5 |
| q-0138 | blocked | no | — | 5 |
| q-0139 | blocked | no | — | 4 |
| q-0145 | blocked | no | — | 6 |
| q-0146 | review | yes | T, U, p | 4 |
| q-0147 | blocked | no | — | 5 |
| q-0148 | blocked | no | — | 5 |
| q-0149 | blocked | no | — | 5 |
| q-0150 | blocked | no | — | 5 |
| q-0152 | blocked | no | — | 5 |
| q-0154 | blocked | no | — | 5 |
| q-0155 | blocked | no | — | 5 |
| q-0156 | blocked | no | — | 5 |
| q-0157 | blocked | no | — | 5 |
| q-0158 | blocked | no | — | 4 |
| q-0175 | blocked | no | — | 4 |
| q-0176 | review | yes | U, Urel, k_m2_s2, nut_m2_s, omega_s_1, p_m2_s2 | 1 |
| q-0177 | blocked | no | — | 6 |
| q-0178 | blocked | no | — | 5 |
| q-0179 | blocked | no | — | 5 |
| q-0180 | blocked | no | — | 6 |
| q-0181 | blocked | no | — | 6 |
| q-0182 | blocked | no | — | 6 |
| q-0183 | blocked | no | — | 5 |
| q-0184 | blocked | no | — | 4 |
| q-0185 | blocked | no | — | 5 |
| q-0186 | blocked | no | — | 5 |
| q-0289 | blocked | no | — | 5 |
| q-0290 | blocked | no | — | 4 |
| q-0291 | review | yes | U.air, kinematicCloud:theta, p | 2 |
| q-0292 | blocked | no | — | 5 |
| q-0293 | blocked | no | — | 5 |
| q-0294 | blocked | no | — | 5 |
| q-0295 | blocked | no | — | 5 |
| q-0297 | blocked | no | — | 5 |
| q-0298 | blocked | no | — | 5 |
| q-0299 | blocked | no | — | 5 |
| q-0300 | blocked | no | — | 4 |
| q-0361 | blocked | no | — | 5 |
| q-0362 | blocked | no | — | 5 |
| q-0363 | blocked | no | — | 5 |
| q-0364 | blocked | no | — | 5 |
| q-0365 | blocked | no | — | 5 |
| q-0366 | blocked | no | — | 5 |
| q-0367 | blocked | no | — | 5 |
| q-0368 | blocked | no | — | 5 |
| q-0369 | blocked | no | — | 5 |
| q-0370 | blocked | no | — | 6 |
| q-0372 | blocked | no | — | 4 |
| q-0373 | blocked | no | — | 5 |
| q-0502 | blocked | no | — | 4 |
| q-0503 | blocked | no | — | 6 |
| q-0505 | review | yes | U, alphat, epsilon, k, nut, p | 5 |
| q-0506 | blocked | no | — | 6 |
| q-0508 | blocked | no | — | 5 |
| q-0509 | blocked | no | — | 5 |
| q-0510 | blocked | no | — | 6 |
| q-0511 | blocked | no | — | 5 |

Scoring anchors: normalized RMSE ≤ 5% and normalized max error ≤ 20% get full credit; normalized RMSE ≥ 30% or max error ≥ 100% get zero credit; intermediate scores are linear and aggregated by the worst field/metric.
