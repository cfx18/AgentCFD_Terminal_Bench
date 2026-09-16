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

[DRAFT: post-processing schema and independently qualified numeric acceptance are not released yet.]
