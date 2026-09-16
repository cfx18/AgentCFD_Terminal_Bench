# Observation and output contract

Read `observations/schema.json` and `observations/fields.csv`. All target samples are public synthetic internal-cell values, not laboratory measurements. Each row contains a physical cell-centre coordinate, a positive native cell-volume quadrature weight, both velocity vectors, kinematic pressure, turbulent kinetic energy, specific dissipation rate and eddy viscosity. Coordinates are observation locations, not a requirement to reuse the reference mesh. Exterior geometry is `geometry/domain.stl`; neutral surface labels do not prescribe boundary roles.

Save standard native `U`, `Urel`, `p`, `k`, `omega` and `nut` volume fields using the dimensions in the schema. The latest selected finite steady state is compared. The reference iteration label is metadata, not elapsed time and not a required iteration count.

A suitable evaluator should sample candidate native fields at every observation coordinate using containing-cell sampling and use the fixed reference-volume weights. Report volume-weighted RMSE, maximum absolute error and normalized forms separately for every field; use vector-magnitude error for velocity. Report both raw pressure error and mean-aligned pressure-shape error rather than silently discarding a pressure offset. Missing coverage and nonfinite values must be reported, not dropped.

The schema contains draft field-specific normalizers but no approved thresholds or reward. In particular, turbulence quantities are closure-dependent and strongly affected by near-wall sampling; expert review and cross-mesh calibration are required before freezing any scoring rule. Reconstruction agreement does not certify continuum convergence or uniquely identify forcing and closure.

The evaluator should independently sample native outputs. A copied target field plus a post-processing-only command is not a calculation. Inputs and restart provenance should remain auditable. Public observations may be used for analysis, but they must not become an initialized or prescribed internal field or a pointwise forcing term.
