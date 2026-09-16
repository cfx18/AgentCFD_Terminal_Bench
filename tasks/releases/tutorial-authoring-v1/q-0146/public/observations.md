# Observation and output contract

Read `/input/observations/schema.json` and `/input/observations/fields.csv`. All 4,000 samples are public synthetic internal-cell values. Every row gives a native cell centre, its positive native cell volume, velocity, temperature, kinematic pressure, reduced kinematic pressure and four closure fields. Coordinates are observation locations, not a requirement to reuse the reference volume mesh. The exterior geometry is `/input/geometry/domain.stl`.

The field dimensions and units are recorded in the schema. In particular, `p` and `p_rgh` have units m2/s2, not Pa. `k` has units m2/s2, `epsilon` has units m2/s3, and `nut` and `alphat` have units m2/s. The observations come from the saved endpoint with iteration index 1000; this index is not physical time. The accompanying VTK files are a redundant visualization export of the same native endpoint.

An evaluator should sample submitted native fields at the observation coordinates using containing-cell sampling and use the supplied cell volumes as quadrature weights. For velocity, compare vector differences. For pressure, report both the raw discrepancy and a separately mean-aligned shape discrepancy; do not silently discard the raw pressure offset. Missing coverage and nonfinite values must be reported rather than dropped. Turbulence-related fields are useful closure diagnostics, but an alternative closure may make them non-comparable even when the primary `U`, `T` and `p` reconstruction is physically plausible.

The reference is a coarse, finite-iteration numerical realization. Small reconstruction error does not certify mesh independence, steady convergence, validity of the Boussinesq approximation at every boundary value, or uniqueness of the inferred thermal forcing.
