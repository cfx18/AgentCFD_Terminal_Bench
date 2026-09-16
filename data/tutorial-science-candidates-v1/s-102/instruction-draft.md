# Steady laminar flow through non-matching connected mesh blocks

Build all OpenFOAM-v2306 input files from an empty workspace. No starter case is provided.

This is a laminar SIMPLE iteration problem, not 100 seconds of transient flow. Keep the 5-versus-7 interface segmentation and cyclicAMI pressure coupling. The right block is skewed; it is not a straight rectangular continuation.

The following geometry, models and initial/boundary data define the task. Coordinates are in metres. Preserve vertex/block order, cell counts, grading and patch names for independently indexed output checks. You may choose linear solvers, relaxation and discretization schemes; these are not reference-matched. Use no larger initial time step or Courant limit than stated. Boundary value entries for wall functions, calculated conditions and outflow initial guesses are numerical initialization, not a new physical constraint.

```json
{
  "solver": "simpleFoam",
  "geometry": {
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
    ],
    "blocks": [
      {
        "vertices": [
          0,
          1,
          2,
          3,
          4,
          5,
          6,
          7
        ],
        "cells": [
          2,
          5,
          1
        ],
        "grading_kind": "simpleGrading",
        "grading": [
          "1",
          "1",
          "1"
        ],
        "cell_zone": "left"
      },
      {
        "vertices": [
          8,
          9,
          10,
          11,
          12,
          13,
          14,
          15
        ],
        "cells": [
          2,
          7,
          1
        ],
        "grading_kind": "simpleGrading",
        "grading": [
          "1",
          "1",
          "1"
        ],
        "cell_zone": "right"
      }
    ],
    "patches": {
      "AMI1": {
        "type": "cyclicAMI",
        "neighbourPatch": "AMI2",
        "transform": "noOrdering",
        "faces": "( ( 2 6 5 1 ) )"
      },
      "AMI2": {
        "type": "cyclicAMI",
        "neighbourPatch": "AMI1",
        "transform": "noOrdering",
        "faces": "( ( 8 12 15 11 ) )"
      },
      "top": {
        "type": "patch",
        "faces": "( ( 3 7 6 2 ) ( 11 15 14 10 ) )"
      },
      "bottom": {
        "type": "patch",
        "faces": "( ( 1 5 4 0 ) ( 9 13 12 8 ) )"
      },
      "left": {
        "type": "patch",
        "faces": "( ( 0 4 7 3 ) )"
      },
      "right": {
        "type": "patch",
        "faces": "( ( 10 14 13 9 ) )"
      },
      "frontAndBack": {
        "type": "empty",
        "faces": "( ( 0 3 2 1 ) ( 4 5 6 7 ) ( 8 11 10 9 ) ( 12 13 14 15 ) )"
      }
    },
    "edges": "( )",
    "merge_patch_pairs": "( )",
    "cell_count": 24
  },
  "models": {
    "kinematic_viscosity_m2_s": 1.5e-05,
    "transport_model": "Newtonian",
    "flow_model": "laminar",
    "custom_model_coefficients": false
  },
  "time": {
    "kind": "steady",
    "start": 0.0,
    "end": 100.0,
    "early_convergence": false,
    "maximum_initial_delta_t": 1.0,
    "adaptive": false,
    "maximum_courant": null
  },
  "fields": {
    "U": {
      "dimensions": "[ 0 1 -1 0 0 0 0 ]",
      "internalField": "uniform ( 0 0 0 )",
      "boundaryField": {
        "AMI1": {
          "type": "cyclicAMI"
        },
        "AMI2": {
          "type": "cyclicAMI"
        },
        "top": {
          "type": "uniformFixedValue",
          "uniformValue": "( 0 0 0 )"
        },
        "bottom": {
          "type": "uniformFixedValue",
          "uniformValue": "( 0 0 0 )"
        },
        "left": {
          "type": "fixedValue",
          "value": "uniform ( 1 0 0 )"
        },
        "right": {
          "type": "inletOutlet",
          "inletValue": "uniform ( 0 0 0 )"
        },
        "frontAndBack": {
          "type": "empty"
        }
      }
    },
    "p": {
      "dimensions": "[ 0 2 -2 0 0 0 0 ]",
      "internalField": "uniform 0",
      "boundaryField": {
        "AMI1": {
          "type": "cyclicAMI",
          "useImplicit": "true"
        },
        "AMI2": {
          "type": "cyclicAMI",
          "useImplicit": "true"
        },
        "top": {
          "type": "zeroGradient"
        },
        "bottom": {
          "type": "zeroGradient"
        },
        "left": {
          "type": "zeroGradient"
        },
        "right": {
          "type": "fixedValue",
          "value": "uniform 0"
        },
        "frontAndBack": {
          "type": "empty"
        }
      }
    }
  },
  "additional_equations": null
}
```

Use ASCII, uncompressed output and write all active final fields. Do not submit a pre-generated mesh, a separate initial phi, moving-mesh physics, added momentum sources or custom model coefficients. Local bare dictionary references such as $p and $internalField are supported; environment/path expansion, dynamic code and arbitrary libraries/includes are not. Read-only probes are allowed. 

Do not seek references, evaluator source, prior results, or external documentation.

[DRAFT: post-processing schema and independently qualified numeric acceptance are not released yet.]
