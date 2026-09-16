# English geometry-only physical tasks

This is the current public-instruction review for s-202, s-203, s-204, and s-205. It supersedes the corresponding Chinese text drafts, without overwriting old experiments, reference fields, qualification records, or scores. The s-10x tasks are out of scope.

The user has accepted the existing numerical cases as Ground Truth. The private [reference selection](ground-truth-selection.json) identifies exactly one completed native reference for each task and retains its known limitations. This approval does not require more author convergence runs. It is not a claim of a new analytic truth or of a fully converged steady reference for every task.

| Task | Physical statement | Execution interface | Measurement definitions |
|---|---|---|---|
| Contact-resistance heat transfer | [Instruction](s-202/instruction.md) | [Protocol](s-202/protocol.md) | [Observations](s-202/observations.md) |
| Temperature-dependent viscosity | [Instruction](s-203/instruction.md) | [Protocol](s-203/protocol.md) | [Observations](s-203/observations.md) |
| Sealed-cavity natural convection | [Instruction](s-204/instruction.md) | [Protocol](s-204/protocol.md) | [Observations](s-204/observations.md) |
| Diaphragm-removal waves | [Instruction](s-205/instruction.md) | [Protocol](s-205/protocol.md) | [Observations](s-205/observations.md) |

## What the evaluated agent receives

The shared `agentcfd_bench.public_task.render` combines each task's complete instruction, protocol, and observations, then lists the supplied read-only geometry. Its public manifest permits only the declared surface files and geometry README as initial assets. No computational volume mesh, numerical scheme, cell count, reference output, author review, or reference-selection manifest is supplied.

The physics statement contains natural-language material, initial, boundary, and constitutive conditions. Required service names, action JSON, supported mesh representations, and measurement keys are deliberately confined to the protocol and observations. The service's remaining mesh-representation restrictions are disclosed, not presented as arbitrary mesh-generation support.

All three public documents, the geometry descriptions, and the rendered task are English. Old Chinese drafts and historical expert reviews remain available as history. English public bundles do not require translating the expert's private review notes or inventing English model responses for old transcripts.

The machine-readable observation schemas mirror the existing independent extractors. The same definitions appear completely in observations.md; the agent is not told to read an unavailable schema file.

## Release boundary

The default YAML now selects this English instruction profile, but it cannot fall back to old fixed-mesh tasks. This change does not publish a revised grader, implement staged reward, raise execution budgets, or start model evaluation. Expert acceptance of Ground Truth and numerical convergence certification are distinct records. The next scoring/release integration must consume the explicit accepted-reference policy rather than falsify old `qualified` results.

The private review and tests are described in [the review report](../../docs/ENGLISH_20X_INSTRUCTION_REVIEW_20260915.md). This README and the reference-selection file are not part of any public task manifest.

## Read-only prompt preview

From the parent workspace, use the same renderer as the execution pipeline:

```bash
PYTHONPATH=AgentCFD_Terminal_Bench .venv-eval/bin/python -B -c 'from agentcfd_bench.public_task import render; print(render("AgentCFD_Terminal_Bench/task-drafts/geometry-only-free-mesh-en-v2/s-204"))'
```

This reads files only. It does not call a model, run OpenFOAM, access an account, or qualify a release.
