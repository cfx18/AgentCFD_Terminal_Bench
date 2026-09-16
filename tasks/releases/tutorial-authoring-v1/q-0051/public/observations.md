# Observation and output contract

Read `/input/observations/schema.json` and `/input/observations/fields.csv`. All target samples are public synthetic internal-cell data. Each row gives a physical cell-centre coordinate, a positive reference-volume quadrature weight, and absolute temperature. Coordinates are observation locations, not a requirement to reuse the reference mesh. Geometry is `/input/geometry/domain.stl`; its neutral region labels do not prescribe boundary conditions.

Save a standard native `T` field with temperature dimensions and units kelvin at physical time 3 s. ASCII and binary native fields are supported by the native sampler. Choose boundary names freely. A report or copied table is not a replacement for a native calculation and saved field.

An evaluator should sample the submitted native temperature at every observation coordinate using containing-cell sampling. Report volume-weighted RMSE, unweighted maximum absolute error, normalized versions using the supplied 298.669 K target range, missing-sample coverage, and nonfinite values. Reference quadrature weights are used only for aggregation; they do not prescribe a candidate mesh. Mesh and sampling error contribute to discrepancy, and these metrics do not certify continuum convergence or uniquely identify boundary forcing.

The target data may be used to calibrate physically interpretable boundary parameters. Do not use the target internal field as an initial or prescribed solution, construct pointwise interior forcing, or submit a postprocessing-only copy of target values. Inputs and restart provenance may be audited.
