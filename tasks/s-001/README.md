# s-001 — Transient Couette flow

## Public problem

See instruction.md for the full public specification and reporting contract.
This is the existing pilot task, not a new or harder question.

## Reference solution

solution/reference.py produces the qualification inputs. These are not starter
files and are never sent to a model. The formula in tests/analytic.py is private.

## Verification

tests/acceptance.py independently reads frozen native output. It checks public
physical constraints, velocity-profile accuracy and reported-number fidelity.
Numerical schemes are not compared literally with the reference configuration.
Release `couette-transient-2` fixes false rejections of disabled switches,
omitted empty mesh lists, unit default scaling, and passive auxiliary inputs.
Physical tolerances and the canonical 4 x 20 x 1 mesh are unchanged. All input
files still undergo the same security scan and native execution. Initial face
flux `0/phi` is not supported: the runtime must derive it from the specified U.
See the project verifier repair report for historical replay, not new model scores.

## Execution

This package uses our durable native submission service, not stock `harbor run`.
task.toml follows Harbor's task layout; metadata.execution_protocol identifies
the extension. The service, rather than agent-authored files, owns run receipts.
No Docker image or fresh real-runtime qualification is claimed by packaging.
