# Execution and submission protocol

The task statement, this protocol, and the observation definitions are supplied together. Read-only geometry is available at the /artifacts/geometry/ paths listed at the end of the task. The working directory is /work; no starting case, volume mesh, or configuration template is provided.

You may use the provided read-only general OpenFOAM v2306 documentation service. Public internet access, other tasks, previous results, reference solutions, and evaluator source are unavailable. Geometry labels identify physical surfaces, not numerical settings.

Write your OpenFOAM input files under 0/, constant/, and system/. Keep auxiliary analysis scripts outside those input directories. The independent execution service snapshots the submitted inputs and runs the supported native workflow; OpenFOAM is not installed in the editing workspace. It does not execute arbitrary submitted shell scripts, Python scripts, custom libraries, or dynamic code. Ordinary local text includes and dictionary macros are supported; external includes and references to host paths are not.

## Run and report

To request a run, write system/science-action.json with the run action shown below, then finish the turn. The independent service returns a run_id and the real fields and sanitized logs under /artifacts/<run_id>/. Read those outputs before preparing the report. A report must refer to your own completed run, not another run or an invented result.

```json
{"action":"run","solver":"buoyantSimpleFoam"}
```

For the final report, use {"action":"report","run_id":"<returned run_id>","measurements":{...}}. Replace the run_id placeholder with the actual returned identifier. Every measurement has exactly {"unit":"<unit from the observation table>","value":<number or array>}. Use all and only the measurement keys, units, and array lengths in the observation table. Scalar measurements are JSON numbers, not one-element arrays. NaN, Infinity, and fabricated values are not accepted.

The service independently extracts measurements from the native output. The reporting consistency tolerance is 1e-6 absolute plus 1e-5 relative; this checks truthful extraction, not physical accuracy against a reference. Use sufficient write precision to preserve the requested observations. A solver exit code of zero alone is not a statement that the physical solution is accurate.

The experiment separately declares the cumulative model-call and native-runtime budgets and each request's watchdog. You may correct and resubmit within those budgets; this protocol adds no failure-count cap, token cap, or fee cap. Do not resubmit an operation whose outcome is still unknown: wait for its existing result. Infrastructure interruption is distinct from an incorrect physical answer.

## Native capabilities for this task

The supported service workflow is blockMesh, checkMesh, and buoyantSimpleFoam, followed by trusted cell-centre/volume exports and wallHeatFlux postprocessing with the thermophysical model loaded. The current observation implementation supports a complete orthogonal Cartesian tensor grid covering the cavity; choose the cell counts and spacing in all three directions. Unstructured or skewed meshes are not supported by this service version.

Keep the geometry labels hot, cold, frontAndBack, and topAndBottom for the corresponding surface groups. Preserve the actual final fields and at least one preceding positive-iteration U and T write from the same mesh. The service returns an independently generated wallHeatFlux field and an area-integrated wall-heat log. Keep the saved iteration numbers visible; the difference between two writes is a diagnostic and does not by itself prove convergence.

Write uncompressed ASCII fields at the actual final time or iteration. The end of the log and the saved fields must refer to the same completed run. Do not submit generated volume meshes, old result directories, precomputed solutions, or substitute postprocessor output for native fields.
