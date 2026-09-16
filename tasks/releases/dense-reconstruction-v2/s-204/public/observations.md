# Observation and output contract

Read `/input/observations/schema.json` and `/input/observations/fields.csv`. All target samples are public. They are synthetic internal-cell values, not laboratory measurements. Each row contains physical coordinates, a positive reference-volume quadrature weight, three velocity components, pressure and absolute temperature. Coordinates are observation locations, not a requirement to use the reference mesh. Geometry is `/input/geometry/domain.stl`; neutral surface labels do not prescribe boundary conditions.

Save standard native `U`, `T` and absolute `p` fields with dimensions m/s, K and Pa respectively. If your formulation evolves reduced pressure, also produce its physically consistent absolute-pressure field. ASCII and binary native fields are supported by the native sampler. Choose your boundary names freely. The latest saved numerical state from your submitted run is compared; the target supplies no physical time or mandatory iteration count.

The evaluator samples your native fields at every observation location using OpenFOAM containing-cell sampling (`cell` interpolation). It uses fixed reference-volume weights to report velocity-vector and scalar RMSE, maximum errors and normalized errors. Missing sample coverage and nonfinite values are reported explicitly, not dropped. Mesh interpolation/discretization contributes to reconstruction error; these metrics do not certify continuum or steady-state convergence.

The normalizing scales are supplied in the schema. Temperature and pressure are scaled by their respective target ranges, not by their absolute means. Both raw absolute-pressure error and a separately mean-aligned pressure-shape error are reported. The absolute pressure level is not silently discarded. A small reconstruction error does not uniquely establish the inferred mechanism or correctness on a different operating condition.

## Frozen scoring rule

The full scoring rule is in `/input/rubric.json`. For each of U, T and p, a normalized
RMSE at or below 0.05 and a normalized maximum error at or below 0.20 earn full
credit. RMSE at or above 0.30 or maximum error at or above 1.0 earns zero credit.
Between these anchors credit decreases linearly. The overall reward is the minimum
over both metrics and all three fields: a poor field cannot be hidden by averaging.
`pass` means full credit; intermediate reward is retained even when below full credit.
These are reconstruction tolerances, not a convergence certificate.

Absolute pressure is scored without any offset correction.

The evaluator independently samples frozen native outputs. A copied field plus a
postprocessing-only command is not a calculation. Inputs are retained to audit
the stated initial condition and provenance of restarts. Custom executable field
hooks or unresolved restart provenance require human review rather than an
automatic physics failure or automatic reward. Ordinary meshing and diagnostics
are available; this is not a hidden configuration-template match.

Public observations may be used for your own comparisons. Submit one chosen
native calculation; the authoritative evaluator is not an iterative tuning tool.
