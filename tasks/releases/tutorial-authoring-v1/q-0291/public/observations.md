# Observation and output contract

Read `/input/observations/schema.json` and `/input/observations/fields.csv`. The 1,155 rows are synthetic native internal-cell observations at physical time 2 s. Each row gives a physical cell-centre coordinate, its positive native cell volume, carrier velocity, kinematic gauge pressure, carrier volume fraction and particle volume fraction. Coordinates are observation locations and volumes are quadrature weights; neither prescribes the candidate volume mesh. Geometry is `/input/geometry/domain.stl`.

The reference also includes ASCII native fields under `/input/observations/native/2` so dimensions and provenance can be audited. The CSV is the neutral dense comparison representation. No temperature target exists.

Candidate sampling should use native containing-cell values at every observation coordinate. Report complete coverage, volume-weighted vector error for carrier velocity, and volume-weighted scalar errors for pressure and particle volume fraction. Report raw pressure error and a separately mean-aligned pressure-shape error; do not silently discard the pressure offset. Carrier fraction is supplied for diagnosis but is algebraically clipped from the reference particle fraction and should not be double-counted as an independent score.

The schema supplies draft field scales, not release thresholds. The particle field is strongly transient and locally overpacked, so reconstruction error does not certify physical validity, convergence or unique mechanism identification. Missing points and nonfinite candidate values must be reported, not dropped.

The evaluator must independently sample native candidate output. A copied target field plus a postprocessing-only command is not a calculation. Inputs are retained to audit the required initially empty, quiescent state. Public observations may support calibration, but must not be used as an initialized solution or pointwise interior forcing.
