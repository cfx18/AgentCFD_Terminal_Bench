# Steady turbulent flow over a backward-facing step

Build all OpenFOAM-v2306 input files from an empty workspace. No starter case is provided.

Use the k-epsilon RAS model and the specified wall functions. End at iteration 2000 or the registered SIMPLE residual criteria; iteration index is not physical time.

The following geometry, models and initial/boundary data define the task. Coordinates are in metres. Preserve vertex/block order, cell counts, grading and patch names for independently indexed output checks. You may choose linear solvers, relaxation and discretization schemes; these are not reference-matched. Cell-zone labels are bookkeeping, not an additional physics constraint. Use no larger initial time step or Courant limit than stated. Boundary value entries for wall functions, calculated conditions and outflow initial guesses are numerical initialization, not a new physical constraint.

```json
{
  "additional_equations": null,
  "fields": {
    "U": {
      "boundaryField": {
        "frontAndBack": {
          "type": "empty"
        },
        "inlet": {
          "type": "fixedValue",
          "value": "uniform ( 10 0 0 )"
        },
        "lowerWall": {
          "type": "noSlip"
        },
        "outlet": {
          "type": "zeroGradient"
        },
        "upperWall": {
          "type": "noSlip"
        }
      },
      "dimensions": "[ 0 1 -1 0 0 0 0 ]",
      "internalField": "uniform ( 0 0 0 )"
    },
    "epsilon": {
      "boundaryField": {
        "frontAndBack": {
          "type": "empty"
        },
        "inlet": {
          "type": "fixedValue",
          "value": "uniform 14.855"
        },
        "lowerWall": {
          "type": "epsilonWallFunction",
          "value": "uniform 14.855"
        },
        "outlet": {
          "type": "zeroGradient"
        },
        "upperWall": {
          "type": "epsilonWallFunction",
          "value": "uniform 14.855"
        }
      },
      "dimensions": "[ 0 2 -3 0 0 0 0 ]",
      "internalField": "uniform 14.855"
    },
    "k": {
      "boundaryField": {
        "frontAndBack": {
          "type": "empty"
        },
        "inlet": {
          "type": "fixedValue",
          "value": "uniform 0.375"
        },
        "lowerWall": {
          "type": "kqRWallFunction",
          "value": "uniform 0.375"
        },
        "outlet": {
          "type": "zeroGradient"
        },
        "upperWall": {
          "type": "kqRWallFunction",
          "value": "uniform 0.375"
        }
      },
      "dimensions": "[ 0 2 -2 0 0 0 0 ]",
      "internalField": "uniform 0.375"
    },
    "nut": {
      "boundaryField": {
        "frontAndBack": {
          "type": "empty"
        },
        "inlet": {
          "type": "calculated",
          "value": "uniform 0"
        },
        "lowerWall": {
          "type": "nutkWallFunction",
          "value": "uniform 0"
        },
        "outlet": {
          "type": "calculated",
          "value": "uniform 0"
        },
        "upperWall": {
          "type": "nutkWallFunction",
          "value": "uniform 0"
        }
      },
      "dimensions": "[ 0 2 -1 0 0 0 0 ]",
      "internalField": "uniform 0"
    },
    "p": {
      "boundaryField": {
        "frontAndBack": {
          "type": "empty"
        },
        "inlet": {
          "type": "zeroGradient"
        },
        "lowerWall": {
          "type": "zeroGradient"
        },
        "outlet": {
          "type": "fixedValue",
          "value": "uniform 0"
        },
        "upperWall": {
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
          18,
          30,
          1
        ],
        "grading": [
          "0.5",
          [
            [
              "1",
              "4",
              "2"
            ],
            [
              "2",
              "3",
              "4"
            ],
            [
              "2",
              "4",
              "0.25"
            ]
          ],
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          0,
          3,
          4,
          1,
          11,
          14,
          15,
          12
        ]
      },
      {
        "cells": [
          180,
          27,
          1
        ],
        "grading": [
          "4",
          "4",
          "4",
          "4",
          [
            [
              "2",
              "4",
              "1"
            ],
            [
              "1",
              "3",
              "0.3"
            ]
          ],
          "1",
          "1",
          [
            [
              "2",
              "4",
              "1"
            ],
            [
              "1",
              "3",
              "0.3"
            ]
          ],
          "1",
          "1",
          "1",
          "1"
        ],
        "grading_kind": "edgeGrading",
        "vertices": [
          2,
          5,
          6,
          3,
          13,
          16,
          17,
          14
        ]
      },
      {
        "cells": [
          180,
          30,
          1
        ],
        "grading": [
          "4",
          "4",
          "4",
          "4",
          [
            [
              "1",
              "4",
              "2"
            ],
            [
              "2",
              "3",
              "4"
            ],
            [
              "2",
              "4",
              "0.25"
            ]
          ],
          [
            [
              "2",
              "1",
              "1"
            ],
            [
              "1",
              "1",
              "0.25"
            ]
          ],
          [
            [
              "2",
              "1",
              "1"
            ],
            [
              "1",
              "1",
              "0.25"
            ]
          ],
          [
            [
              "1",
              "4",
              "2"
            ],
            [
              "2",
              "3",
              "4"
            ],
            [
              "2",
              "4",
              "0.25"
            ]
          ],
          "1",
          "1",
          "1",
          "1"
        ],
        "grading_kind": "edgeGrading",
        "vertices": [
          3,
          6,
          7,
          4,
          14,
          17,
          18,
          15
        ]
      },
      {
        "cells": [
          25,
          27,
          1
        ],
        "grading": [
          "2.5",
          "1",
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          5,
          8,
          9,
          6,
          16,
          19,
          20,
          17
        ]
      },
      {
        "cells": [
          25,
          30,
          1
        ],
        "grading": [
          "2.5",
          [
            [
              "2",
              "1",
              "1"
            ],
            [
              "1",
              "1",
              "0.25"
            ]
          ],
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          6,
          9,
          10,
          7,
          17,
          20,
          21,
          18
        ]
      }
    ],
    "cell_count": 12225,
    "edges": "( )",
    "merge_patch_pairs": "( )",
    "patches": {
      "frontAndBack": {
        "faces": "( ( 0 3 4 1 ) ( 2 5 6 3 ) ( 3 6 7 4 ) ( 5 8 9 6 ) ( 6 9 10 7 ) ( 11 14 15 12 ) ( 13 16 17 14 ) ( 14 17 18 15 ) ( 16 19 20 17 ) ( 17 20 21 18 ) )",
        "type": "empty"
      },
      "inlet": {
        "faces": "( ( 0 1 12 11 ) )",
        "type": "patch"
      },
      "lowerWall": {
        "faces": "( ( 0 3 14 11 ) ( 3 2 13 14 ) ( 2 5 16 13 ) ( 5 8 19 16 ) )",
        "type": "wall"
      },
      "outlet": {
        "faces": "( ( 8 9 20 19 ) ( 9 10 21 20 ) )",
        "type": "patch"
      },
      "upperWall": {
        "faces": "( ( 1 4 15 12 ) ( 4 7 18 15 ) ( 7 10 21 18 ) )",
        "type": "wall"
      }
    },
    "vertices_m": [
      [
        -0.0206,
        0.0,
        -0.0005
      ],
      [
        -0.0206,
        0.0254,
        -0.0005
      ],
      [
        0.0,
        -0.0254,
        -0.0005
      ],
      [
        0.0,
        0.0,
        -0.0005
      ],
      [
        0.0,
        0.0254,
        -0.0005
      ],
      [
        0.206,
        -0.0254,
        -0.0005
      ],
      [
        0.206,
        0.0,
        -0.0005
      ],
      [
        0.206,
        0.0254,
        -0.0005
      ],
      [
        0.29,
        -0.0166,
        -0.0005
      ],
      [
        0.29,
        0.0,
        -0.0005
      ],
      [
        0.29,
        0.0166,
        -0.0005
      ],
      [
        -0.0206,
        0.0,
        0.0005
      ],
      [
        -0.0206,
        0.0254,
        0.0005
      ],
      [
        0.0,
        -0.0254,
        0.0005
      ],
      [
        0.0,
        0.0,
        0.0005
      ],
      [
        0.0,
        0.0254,
        0.0005
      ],
      [
        0.206,
        -0.0254,
        0.0005
      ],
      [
        0.206,
        0.0,
        0.0005
      ],
      [
        0.206,
        0.0254,
        0.0005
      ],
      [
        0.29,
        -0.0166,
        0.0005
      ],
      [
        0.29,
        0.0,
        0.0005
      ],
      [
        0.29,
        0.0166,
        0.0005
      ]
    ]
  },
  "models": {
    "custom_model_coefficients": false,
    "flow_model": "RAS/kEpsilon",
    "kinematic_viscosity_m2_s": 1e-05,
    "transport_model": "Newtonian"
  },
  "solver": "simpleFoam",
  "time": {
    "adaptive": false,
    "early_convergence": true,
    "end": 2000.0,
    "kind": "steady",
    "maximum_courant": null,
    "maximum_initial_delta_t": 1.0,
    "start": 0.0,
    "steady_residual_criteria": {
      "\"(k|epsilon|omega|f|v2)\"": "1e-3",
      "U": "1e-3",
      "p": "1e-2"
    }
  }
}
```

Use ASCII, uncompressed output and write all active final fields. Do not submit a pre-generated mesh, a separate initial phi, moving-mesh physics, added momentum sources or custom model coefficients. Local bare dictionary references such as $p and $internalField are supported; environment/path expansion, dynamic code and arbitrary libraries/includes are not. Read-only probes are allowed. The standard streamlines function and its pinned standard include are supported but are not an extra physical equation. 

Do not seek references, evaluator source, prior results, or external documentation.

[DRAFT: post-processing schema and independently qualified numeric acceptance are not released yet.]
