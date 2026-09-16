# Transient lid-driven enclosed flow

Build all OpenFOAM-v2306 input files from an empty workspace. No starter case is provided.

This is a closed, transient flow at Re=10. No slip on the stationary in-plane walls; front/back are empty, not no-slip walls.

The following geometry, models and initial/boundary data define the task. Coordinates are in metres. Preserve vertex/block order, cell counts, grading and patch names for independently indexed output checks. You may choose linear solvers, relaxation and discretization schemes; these are not reference-matched. Use no larger initial time step or Courant limit than stated. Boundary value entries for wall functions, calculated conditions and outflow initial guesses are numerical initialization, not a new physical constraint.

```json
{
  "solver": "icoFoam",
  "geometry": {
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
          20,
          20,
          1
        ],
        "grading_kind": "simpleGrading",
        "grading": [
          "1",
          "1",
          "1"
        ]
      }
    ],
    "patches": {
      "movingWall": {
        "type": "wall",
        "faces": "( ( 3 7 6 2 ) )"
      },
      "fixedWalls": {
        "type": "wall",
        "faces": "( ( 0 4 7 3 ) ( 2 6 5 1 ) ( 1 5 4 0 ) )"
      },
      "frontAndBack": {
        "type": "empty",
        "faces": "( ( 0 3 2 1 ) ( 4 5 6 7 ) )"
      }
    },
    "edges": "( )",
    "merge_patch_pairs": "( )",
    "cell_count": 400
  },
  "models": {
    "kinematic_viscosity_m2_s": 0.01,
    "transport_model": "Newtonian",
    "flow_model": "laminar",
    "custom_model_coefficients": false
  },
  "time": {
    "kind": "transient",
    "start": 0.0,
    "end": 0.5,
    "early_convergence": false,
    "maximum_initial_delta_t": 0.005,
    "adaptive": false,
    "maximum_courant": null
  },
  "fields": {
    "U": {
      "dimensions": "[ 0 1 -1 0 0 0 0 ]",
      "internalField": "uniform ( 0 0 0 )",
      "boundaryField": {
        "movingWall": {
          "type": "fixedValue",
          "value": "uniform ( 1 0 0 )"
        },
        "fixedWalls": {
          "type": "noSlip"
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
        "movingWall": {
          "type": "zeroGradient"
        },
        "fixedWalls": {
          "type": "zeroGradient"
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
