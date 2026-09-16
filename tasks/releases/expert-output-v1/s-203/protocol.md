# Execution and submission protocol

The task statement, this protocol, and the observation definitions are supplied together. Read-only geometry is available at the /artifacts/geometry/ paths listed at the end of the task. The working directory is /work; no starting case, volume mesh, or configuration template is provided.

You may use the provided read-only general OpenFOAM v2306 documentation service. Public internet access, other tasks, previous results, reference solutions, and evaluator source are unavailable. Geometry labels identify physical surfaces, not numerical settings.

Write your OpenFOAM input files under 0/, constant/, and system/. Keep auxiliary analysis scripts outside those input directories. The independent execution service snapshots the submitted inputs and runs the supported native workflow; OpenFOAM is not installed in the editing workspace. It does not execute arbitrary submitted shell scripts, Python scripts, custom libraries, or dynamic code. Ordinary local text includes and dictionary macros are supported; external includes and references to host paths are not.

## Run and report

To request a run, write system/science-action.json with the run action shown below, then finish the turn. The independent service returns a run_id and the real fields and sanitized logs under /artifacts/<run_id>/. Read those outputs before preparing the report. A report must refer to your own completed run, not another run or an invented result.

```json
{"action":"run","solver":"pimpleFoam"}
```

For the final report, use {"action":"report","run_id":"<returned run_id>","measurements":{...}}. Replace the run_id placeholder with the actual returned identifier. Every measurement has exactly {"unit":"<unit from the observation table>","value":<number or array>}. Use all and only the measurement keys, units, and array lengths in the observation table. Scalar measurements are JSON numbers, not one-element arrays. NaN, Infinity, and fabricated values are not accepted.

The service independently extracts measurements from the native output. The reporting consistency tolerance is 1e-6 absolute plus 1e-5 relative; this checks truthful extraction, not physical accuracy against a reference. Use sufficient write precision to preserve the requested observations. A solver exit code of zero alone is not a statement that the physical solution is accurate.

The experiment separately declares the cumulative model-call and native-runtime budgets and each request's watchdog. You may correct and resubmit within those budgets; this protocol adds no failure-count cap, token cap, or fee cap. Do not resubmit an operation whose outcome is still unknown: wait for its existing result. Infrastructure interruption is distinct from an incorrect physical answer.

## Native capabilities for this task

The supported service workflow is blockMesh, checkMesh, and pimpleFoam, followed by trusted cell-centre/volume and face-flux export. You must supply the coupled energy-transport and viscous-heating inputs needed for the physical problem. The service does not add the physical energy equation for you.

Use the physical opening labels inlet, outlet1, and outlet2 and the remaining wall group defaultFaces. The current service supports connected orthogonal block meshes; choose their resolution and grading yourself. Other mesh-generation workflows are not supported by this service version. The final native temperature field and actual energy-equation execution are required, even if the flow solver alone can exit without them.

Write uncompressed ASCII fields at the actual final time or iteration. The end of the log and the saved fields must refer to the same completed run. Do not submit generated volume meshes, old result directories, precomputed solutions, or substitute postprocessor output for native fields.
