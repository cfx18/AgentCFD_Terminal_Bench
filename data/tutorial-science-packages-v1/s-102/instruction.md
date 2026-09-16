# Steady laminar flow through non-matching connected mesh blocks

Build all OpenFOAM-v2306 input files from an empty workspace. No starter case is provided.

This is a laminar SIMPLE iteration problem, not 100 seconds of transient flow. Keep the 5-versus-7 interface segmentation and cyclicAMI pressure coupling. The right block is skewed; it is not a straight rectangular continuation.

The following geometry, models and initial/boundary data define the task. Coordinates are in metres. Preserve vertex/block order, cell counts, grading and patch names for independently indexed output checks. You may choose linear solvers, relaxation and discretization schemes; these are not reference-matched. Cell-zone labels are bookkeeping, not an additional physics constraint. Use no larger initial time step or Courant limit than stated. Boundary value entries for wall functions, calculated conditions and outflow initial guesses are numerical initialization, not a new physical constraint.

```json
{
  "additional_equations": null,
  "fields": {
    "U": {
      "boundaryField": {
        "AMI1": {
          "type": "cyclicAMI"
        },
        "AMI2": {
          "type": "cyclicAMI"
        },
        "bottom": {
          "type": "uniformFixedValue",
          "uniformValue": "( 0 0 0 )"
        },
        "frontAndBack": {
          "type": "empty"
        },
        "left": {
          "type": "fixedValue",
          "value": "uniform ( 1 0 0 )"
        },
        "right": {
          "inletValue": "uniform ( 0 0 0 )",
          "type": "inletOutlet"
        },
        "top": {
          "type": "uniformFixedValue",
          "uniformValue": "( 0 0 0 )"
        }
      },
      "dimensions": "[ 0 1 -1 0 0 0 0 ]",
      "internalField": "uniform ( 0 0 0 )"
    },
    "p": {
      "boundaryField": {
        "AMI1": {
          "type": "cyclicAMI",
          "useImplicit": "true"
        },
        "AMI2": {
          "type": "cyclicAMI",
          "useImplicit": "true"
        },
        "bottom": {
          "type": "zeroGradient"
        },
        "frontAndBack": {
          "type": "empty"
        },
        "left": {
          "type": "zeroGradient"
        },
        "right": {
          "type": "fixedValue",
          "value": "uniform 0"
        },
        "top": {
          "type": "zeroGradient"
        }
      },
      "dimensions": "[ 0 2 -2 0 0 0 0 ]",
      "internalField": "uniform 0"
    }
  },
  "geometry": {
    "blocks": [
      {
        "cell_zone": "left",
        "cells": [
          2,
          5,
          1
        ],
        "grading": [
          "1",
          "1",
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          0,
          1,
          2,
          3,
          4,
          5,
          6,
          7
        ]
      },
      {
        "cell_zone": "right",
        "cells": [
          2,
          7,
          1
        ],
        "grading": [
          "1",
          "1",
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          8,
          9,
          10,
          11,
          12,
          13,
          14,
          15
        ]
      }
    ],
    "cell_count": 24,
    "edges": "( )",
    "merge_patch_pairs": "( )",
    "patches": {
      "AMI1": {
        "faces": "( ( 2 6 5 1 ) )",
        "neighbourPatch": "AMI2",
        "transform": "noOrdering",
        "type": "cyclicAMI"
      },
      "AMI2": {
        "faces": "( ( 8 12 15 11 ) )",
        "neighbourPatch": "AMI1",
        "transform": "noOrdering",
        "type": "cyclicAMI"
      },
      "bottom": {
        "faces": "( ( 1 5 4 0 ) ( 9 13 12 8 ) )",
        "type": "patch"
      },
      "frontAndBack": {
        "faces": "( ( 0 3 2 1 ) ( 4 5 6 7 ) ( 8 11 10 9 ) ( 12 13 14 15 ) )",
        "type": "empty"
      },
      "left": {
        "faces": "( ( 0 4 7 3 ) )",
        "type": "patch"
      },
      "right": {
        "faces": "( ( 10 14 13 9 ) )",
        "type": "patch"
      },
      "top": {
        "faces": "( ( 3 7 6 2 ) ( 11 15 14 10 ) )",
        "type": "patch"
      }
    },
    "vertices_m": [
      [
        0.0,
        0.0,
        0.0
      ],
      [
        0.05,
        0.0,
        0.0
      ],
      [
        0.05,
        0.1,
        0.0
      ],
      [
        0.0,
        0.1,
        0.0
      ],
      [
        0.0,
        0.0,
        0.01
      ],
      [
        0.05,
        0.0,
        0.01
      ],
      [
        0.05,
        0.1,
        0.01
      ],
      [
        0.0,
        0.1,
        0.01
      ],
      [
        0.05,
        0.0,
        0.0
      ],
      [
        0.1,
        0.1,
        0.0
      ],
      [
        0.1,
        0.2,
        0.0
      ],
      [
        0.05,
        0.1,
        0.0
      ],
      [
        0.05,
        0.0,
        0.01
      ],
      [
        0.1,
        0.1,
        0.01
      ],
      [
        0.1,
        0.2,
        0.01
      ],
      [
        0.05,
        0.1,
        0.01
      ]
    ]
  },
  "models": {
    "custom_model_coefficients": false,
    "flow_model": "laminar",
    "kinematic_viscosity_m2_s": 1.5e-05,
    "transport_model": "Newtonian"
  },
  "solver": "simpleFoam",
  "time": {
    "adaptive": false,
    "early_convergence": false,
    "end": 100.0,
    "kind": "steady",
    "maximum_courant": null,
    "maximum_initial_delta_t": 1.0,
    "start": 0.0
  }
}
```

Use ASCII, uncompressed output and write all active final fields. Do not submit a pre-generated mesh, a separate initial phi, moving-mesh physics, added momentum sources or custom model coefficients. Local bare dictionary references such as $p and $internalField are supported; environment/path expansion, dynamic code and arbitrary libraries/includes are not. Read-only probes are allowed. 

Do not seek references, evaluator source, prior results, or external documentation.

## Real execution and independent postprocessing

Write system/science-action.json with exactly {"action": "run", "solver": "simpleFoam"} and finish the current harness turn. The separate service snapshots your inputs, runs blockMesh, checkMesh and the registered solver, then resumes this same session with native feedback.
The solver is not mounted in your workspace; do not claim execution from a local shell. There is no fixed failed-submission count. Every model API call, including auxiliary calls, uses the remaining total call budget. You may change files and submit another official run.

After successful execution, native fields and sanitized logs are read-only under /artifacts/<run_id>/. Write your own postprocessor outside 0/, constant/ and system/ in /work. Do not submit generated mesh or previous result directories. Calculate the following metrics from the actual final internal fields and solver.log, then replace the action file with this shape (zeros are placeholders, not expected values):

```json
{
  "action": "report",
  "run_id": "r-000001",
  "measurements": {
    "final_iteration": {
      "unit": "1",
      "value": 0
    },
    "cell_count": {
      "unit": "1",
      "value": 0
    },
    "U_cell_mean": {
      "unit": "m/s",
      "value": [
        0,
        0,
        0
      ]
    },
    "speed_cell_rms": {
      "unit": "m/s",
      "value": 0
    },
    "speed_cell_max": {
      "unit": "m/s",
      "value": 0
    },
    "p_last_initial_residual": {
      "unit": "1",
      "value": 0
    },
    "p_last_final_residual": {
      "unit": "1",
      "value": 0
    },
    "p_cell_min_mean_max": {
      "unit": "m2/s2",
      "value": [
        0,
        0,
        0
      ]
    }
  }
}
```

U_cell_mean is [mean(Ux), mean(Uy), mean(Uz)] over all internal cells. speed_cell_rms is sqrt(sum(Ux^2+Uy^2+Uz^2)/N); speed_cell_max is max(sqrt(Ux^2+Uy^2+Uz^2)). Each <field>_cell_min_mean_max is [minimum, arithmetic mean, maximum] of that scalar internal field. All these statistics are UNWEIGHTED by cell volume. This is intentional for the prescribed mesh, and must not be reported as a physical volume average. Pressure p is kinematic pressure in m2/s2, not Pa.
cell_count is the number of internal mesh cells. final_time is in seconds for a transient task; final_iteration is a dimensionless SIMPLE iteration for a steady task. The final write must match the last native solver time/iteration, not an earlier available output.
p_last_initial_residual and p_last_final_residual come from the last Solving for p line in the LAST time/iteration block. These residuals are diagnostics, not correctness thresholds.

The verifier independently parses native outputs and checks each reported number with tolerance 1e-6 absolute + 1e-5 relative. Invalid/missing units, nonfinite numbers and wrong list sizes are not inferred. You can correct a failed report or run again within the same remaining budget.

## Fixed-discretization physical acceptance

The public geometry, mesh ordering, initial/boundary conditions and active equations must hold. A native exit code alone is not a pass. In addition to your report, ALL final field cells are compared to a hidden, fully executed original reference on the prescribed discretization. This pilot does not claim a mesh-independent or experimentally validated continuum solution. Numerical dictionaries are not matched to reference files.
For each scalar (and flattened xyz velocity vector), relative L2 = RMS(observed-reference) / max(RMS(reference),1e-12); relative Linf = max(abs(observed-reference)) / max(max(abs(reference)),1e-12). Permitted errors are:

```json
{
  "U": {
    "relative_l2": 0.1,
    "relative_linf": 0.5
  },
  "p": {
    "relative_l2": 0.15,
    "relative_linf": 0.5
  }
}
```

Outlet pressure anchors the gauge: compare absolute kinematic p; no arbitrary shift is allowed.
k, epsilon and nut must be nonnegative (roundoff allowance 1e-10). When s is active, require -1e-6 <= s <= final_time+1e-4, in addition to its field comparison and source specification.
Reference values and numeric differences are private. Feedback contains only check outcomes and the names of any report metrics inconsistent with your own native output.
