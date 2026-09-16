# English s-20x instruction review and accepted numerical references

## Decision and scope

On 2026-09-15 the expert accepted the prepared cases as Ground Truth and requested a review and English rewrite of the task instructions. The current scope is s-202 through s-205 only. No s-10x repair, model call, new OpenFOAM run, or additional convergence study is part of this change.

The selected references are approved finite-resolution numerical targets. Historical convergence warnings remain evidence, not a veto on the expert's decision. Approval is recorded separately from automated qualification; no failed scientific check has been rewritten as a pass.

## Public instruction defects addressed

| Task | Defect in the previous short draft | Correction in the English statement |
|---|---|---|
| All four | Chinese public text, dangling protocol references, and author-only warnings inside some statements | Complete English instruction/protocol/observations bundles; private review stays outside the rendered input |
| All four | Mesh freedom and actual service capabilities could be confused | No mesh sizes or configuration recipes in the physics statement; supported native workflows and representation limits are disclosed separately |
| s-202 | Missing fluid opening conditions and potentially ambiguous pressure references | Water and air throughflows, velocities, inlet/outlet temperatures, reverse-flow behavior, gravity, and distinct gauge/absolute reduced-pressure conventions are stated |
| s-202 | Water above its ordinary boiling point could invite a different, reasonable physical model | Explicitly approved single-phase, constant-property water; no boiling, latent heat, or radiation; ideal-gas air remains temperature dependent in density |
| s-202 | Selection tolerances could be mistaken for physical dimensions; two-sided contact data could imply two layers | Keep actual supplied material surfaces, 8 mm plates and the actual heater width; specify one zero-storage interfacial resistance of 2 m2 K/W |
| s-203 | Omitted turbulent thermal transport parameter and ambiguous pressure/energy interpretation | State turbulent Prandtl number 1, kinematic total vs static pressure, initial turbulence, backflow, and coupled temperature/viscous dissipation |
| s-204 | Absolute initial pressure, closed mass, turbulence initial state, and thermal turbulence parameter missing from the short public draft | State 100000 Pa initial absolute pressure, mass conservation, evolving mean pressure, initial k/omega, and turbulent Prandtl number 0.85 |
| s-204 | Failure to distinguish a steady physical target from finite iteration output | Ask for a steady solution and honest convergence evidence; still request the actual available result when strict convergence is not achieved |
| s-205 | Risk of confusing the removed diaphragm with a wall, or sensible energy with a constant formation offset | Specify the initial-state interface, one-dimensional inviscid physics, end conditions, and exact reported sensible-energy definition |

The reference input files, region overrides, thermophysical data, and existing extraction code were inspected, not just the old prose. Inactive laminar turbulence placeholders in s-202 are not promoted into physical requirements. The different air molar masses (28.9 for s-202, 28.96 for s-204/s-205) are preserved rather than silently unified.

## Explicit reference selection

| Task | Selected existing result | Selection reason | Retained limitation |
|---|---|---|---|
| s-202 | corrected coupled coarse case, 100 s, thermal batch 009 | Coupling correction and pressure logs are both present | No claim of mesh/time independence for this corrected case |
| s-203 | finest completed mesh, 68,107 cells, 1.5 s, thermal batch 006 | Existing finest result; no new refinement | Recorded pressure/turbulence mesh differences remain; 495.90 s native duration |
| s-204 | original numerical strategy, 78,750 cells, iteration 6000, buoyant batch 001 | Original finer reference, not the later coarse upwind diagnostic | Finite-iteration state; full steady convergence is not demonstrated; 1041.76 s native duration |
| s-205 | 400-cell result at 0.007 s, buoyant/shock batch 001 | Finest recorded native wave solution; independent Riemann check retained | Existing analytic scoring is not silently replaced by this selection |

The last two temperature plots were not two different agents. For s-204 the upper-row reference is selected; the lower-row upwind run stays a diagnostic. These are explicit implementation selections under the expert's case-level approval, not a claim that the expert individually nominated each run identifier.

Exact paths, input/result/artifact identities, environment versions, approval status, and limitations are in [ground-truth-selection.json](../task-drafts/geometry-only-free-mesh-en-v2/ground-truth-selection.json). All four sources were checked read-only with `completed_operation`; each has an intact successful native result and a resource-release receipt. That is an evidence check, not another numerical solve.

## What this change does not do

- It does not reopen the accepted references for mandatory convergence studies.
- It does not implement the proposed staged reward or change any historical score.
- It does not claim the existing strict graders already implement the newly accepted finite-reference policy. A matching scoring/release binding is still a separate implementation step.
- It does not raise the current 300 s model per-run execution limit. Reference runs longer than that are disclosed; this review alone does not establish that the requested accuracy is achievable at that budget.
- It does not add support for arbitrary meshes. In particular, the current s-204 extractor requires an orthogonal tensor grid, and the current s-205 extractor assumes one layer on each invariant transverse axis. These limits are public in protocol.md, not hidden physical requirements.
- It does not claim exact cross-cell overlap is already implemented for the thermal diagnostic bins: the current s-202/s-203 spatial diagnostic groups cells by centre. The published report quantities here are the implemented volume/flux observations; later reward integration must explicitly handle that approximation.
- Existing static contracts still compare some implementation choices and auxiliary initial fields against the reference. They are not a complete recognizer of physically equivalent OpenFOAM representations. A later scoring integration must not interpret a rejected equivalent implementation as proof that the English physical specification was misunderstood; expanding the instruction into a dictionary answer sheet is not the remedy.

## Implementation and verification

The new version is [geometry-only-free-mesh-en-v2](../task-drafts/geometry-only-free-mesh-en-v2/README.md). The default campaign selects it without changing model, harness, excluded-model list, budget, or network condition. An unsupported draft cannot silently compile into an older registered task.

The shared public renderer's geometry heading is now English. The buoyant/shock material exporter reads the reviewed English bundle and checks its observation schema against the extractor, preventing a later export from reverting to the old Chinese draft. No historical frozen package is modified.

Regression checks cover English public text, complete prompt assembly, geometry identity, private-reference exclusion, instruction/configuration separation, report keys/units/lengths, essential physical conditions, reference evidence identity, English exporter output, and prevention of an unintended paid launch. The final affected-module run passed **265 tests, with zero failures/errors/skips**; see [test evidence and complete public previews](../audits/english-20x-review-20260915-001/README.md). This is not a new full-repository or real-model qualification, and automated checks do not replace expert physical review.
