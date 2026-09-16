# Dense reconstruction v2: runtime requalification

The public problem statements, geometry, observations, ground truth and reward
anchors are unchanged from v1. This version rebinds qualification evidence to the
execution library supporting unlimited native time and durable dispatch ordering.

The experiment selects its budget and completion policy separately:
`experiments/dense-reconstruction-astra-120.yaml` uses 120 provider calls, no task
wall-clock/native-time cap, and deterministic budget-end evaluation. An explicit
Agent submission takes priority; otherwise the latest successfully exited native
run is evaluated, without selecting by ground-truth score. This rule is disclosed
in the public execution protocol, not hidden in the grader.

The full 213-test regression evidence and a fresh native reference sampling replay
are bound in each task's private qualification package. Additional CLI boundary
tests and preparation results are documented in `docs/budget-finalization-120.md`.
No paid model evaluation was launched as part of this release.
