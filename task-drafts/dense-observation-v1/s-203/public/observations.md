# Observation and output contract

Read `/input/observations/schema.json` and `/input/observations/fields.csv`. All target samples are public. They are synthetic internal-cell values, not laboratory measurements. Each row contains physical coordinates, a positive reference-volume quadrature weight, three velocity components, pressure and absolute temperature. Coordinates are observation locations, not a requirement to use the reference mesh. Geometry is `/input/geometry/domain.stl`; neutral surface labels do not prescribe boundary conditions.

Save standard native `U`, `T` and `p` fields with dimensions m/s, K and m2/s2 respectively, at physical time 1.5 s. ASCII and binary native fields are supported by the native sampler. Choose your boundary names freely. A final report is not a replacement for saved native fields.

The independent evaluator samples your native fields at every observation location using OpenFOAM containing-cell sampling (`cell` interpolation). It uses the fixed reference-volume weights to report velocity-vector and scalar RMSE, maximum errors and normalized errors. Missing sample coverage and nonfinite values are reported explicitly, not dropped from the comparison. Mesh interpolation/discretization contributes to reconstruction error; these metrics do not assert continuum convergence.

The normalizing scales are supplied in the schema. Temperature is scaled by the target temperature range, not its roughly 315 K absolute level. Pressure uses the target pressure range; both raw pressure discrepancy and a separately mean-aligned shape error are reported. No pressure offset is silently removed. A zero error at public observations is not evidence of prediction in unseen conditions.

This draft reports raw metrics only. Pass thresholds, a combined reward and mechanism-identification scores have not been released. Public observations can be used for your own comparisons; the authoritative evaluation reads a frozen native run after final submission. Do not repeatedly submit to query a private checker.
