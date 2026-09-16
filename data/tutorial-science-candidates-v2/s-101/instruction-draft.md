# Transient lid-driven enclosed flow

Build all OpenFOAM-v2306 input files from an empty workspace. No starter case is provided.

This is a closed, transient flow at Re=10. No slip on the stationary in-plane walls; front/back are empty, not no-slip walls.

The following geometry, models and initial/boundary data define the task. Coordinates are in metres. Preserve vertex/block order, cell counts, grading and patch names for independently indexed output checks. You may choose linear solvers, relaxation and discretization schemes; these are not reference-matched. Cell-zone labels are bookkeeping, not an additional physics constraint. Use no larger initial time step or Courant limit than stated. Boundary value entries for wall functions, calculated conditions and outflow initial guesses are numerical initialization, not a new physical constraint.

```json
{
  "additional_equations": null,
  "fields": {
    "U": {
      "boundaryField": {
        "fixedWalls": {
          "type": "noSlip"
        },
        "frontAndBack": {
          "type": "empty"
        },
        "movingWall": {
          "type": "fixedValue",
          "value": "uniform ( 1 0 0 )"
        }
      },
      "dimensions": "[ 0 1 -1 0 0 0 0 ]",
      "internalField": "uniform ( 0 0 0 )"
    },
    "p": {
      "boundaryField": {
        "fixedWalls": {
          "type": "zeroGradient"
        },
        "frontAndBack": {
          "type": "empty"
        },
        "movingWall": {
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
        "cells": [
          20,
          20,
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
      }
    ],
    "cell_count": 400,
    "edges": "( )",
    "merge_patch_pairs": "( )",
    "patches": {
      "fixedWalls": {
        "faces": "( ( 0 4 7 3 ) ( 2 6 5 1 ) ( 1 5 4 0 ) )",
        "type": "wall"
      },
      "frontAndBack": {
        "faces": "( ( 0 3 2 1 ) ( 4 5 6 7 ) )",
        "type": "empty"
      },
      "movingWall": {
        "faces": "( ( 3 7 6 2 ) )",
        "type": "wall"
      }
    },
    "vertices_m": [
      [
        0.0,
        0.0,
        0.0
      ],
      [
        0.1,
        0.0,
        0.0
      ],
      [
        0.1,
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
        0.1,
        0.0,
        0.01
      ],
      [
        0.1,
        0.1,
        0.01
      ],
      [
        0.0,
        0.1,
        0.01
      ]
    ]
  },
  "models": {
    "custom_model_coefficients": false,
    "flow_model": "laminar",
    "kinematic_viscosity_m2_s": 0.01,
    "transport_model": "Newtonian"
  },
  "solver": "icoFoam",
  "time": {
    "adaptive": false,
    "early_convergence": false,
    "end": 0.5,
    "kind": "transient",
    "maximum_courant": null,
    "maximum_initial_delta_t": 0.005,
    "start": 0.0
  }
}
```

Use ASCII, uncompressed output and write all active final fields. Do not submit a pre-generated mesh, a separate initial phi, moving-mesh physics, added momentum sources or custom model coefficients. Local bare dictionary references such as $p and $internalField are supported; environment/path expansion, dynamic code and arbitrary libraries/includes are not. Read-only probes are allowed. 

Do not seek references, evaluator source, prior results, or external documentation.

[DRAFT: post-processing schema and independently qualified numeric acceptance are not released yet.]
