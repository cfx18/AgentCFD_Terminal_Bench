# Observation and output contract

Read `/input/observations/schema.json` and `/input/observations/fields.csv`. All target samples are public. They are synthetic internal-cell values, not laboratory measurements. Each row contains physical coordinates, a positive reference-volume quadrature weight, three velocity components, pressure and absolute temperature. Coordinates are observation locations, not a requirement to use the reference mesh. Geometry is `/input/geometry/domain.stl`; neutral surface labels do not prescribe boundary conditions.

Save standard native `U`, `T` and `p` fields with dimensions m/s, K and m2/s2 respectively, at physical time 1.5 s. ASCII and binary native fields are supported by the native sampler. Choose your boundary names freely. A final report is not a replacement for saved native fields.

The independent evaluator samples your native fields at every observation location using OpenFOAM containing-cell sampling (`cell` interpolation). It uses the fixed reference-volume weights to report velocity-vector and scalar RMSE, maximum errors and normalized errors. Missing sample coverage and nonfinite values are reported explicitly, not dropped from the comparison. Mesh interpolation/discretization contributes to reconstruction error; these metrics do not assert continuum convergence.

The normalizing scales are supplied in the schema. Temperature is scaled by the target temperature range, not its roughly 315 K absolute level. Pressure uses the target pressure range; both raw pressure discrepancy and a separately mean-aligned shape error are reported. No pressure offset is silently removed. A zero error at public observations is not evidence of prediction in unseen conditions.

## Frozen scoring rule

The full scoring rule is in `/input/rubric.json`. For each of U, T and p, a normalized
RMSE at or below 0.05 and a normalized maximum error at or below 0.20 earn full
credit. RMSE at or above 0.30 or maximum error at or above 1.0 earns zero credit.
Between these anchors credit decreases linearly. The overall reward is the minimum
over both metrics and all three fields: a poor field cannot be hidden by averaging.
`pass` means full credit; intermediate reward is retained even when below full credit.
These are reconstruction tolerances, not a convergence certificate.

For this task only, remove the volume-weighted constant pressure discrepancy before scoring pressure shape. The raw bias is still recorded.

The evaluator independently samples frozen native outputs. A copied field plus a
postprocessing-only command is not a calculation. Inputs are retained to audit
the stated initial condition and provenance of restarts. Custom executable field
hooks or unresolved restart provenance require human review rather than an
automatic physics failure or automatic reward. Ordinary meshing and diagnostics
are available; this is not a hidden configuration-template match.

Public observations may be used for your own comparisons. Submit one chosen
native calculation; the authoritative evaluator is not an iterative tuning tool.
