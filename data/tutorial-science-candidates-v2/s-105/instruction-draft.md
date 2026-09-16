# Pressure-driven branching flow with a transported scalar and volume source

Build all OpenFOAM-v2306 input files from an empty workspace. No starter case is provided.

This is a three-dimensional duct, including no-slip front/back walls. outlet1 is at y=-0.21 m with kinematic pressure 10 m2/s2; outlet2 is at y=+0.21 m with pressure zero. Inlet total pressure is 10+30*t for 0<=t<=1 second and 40 thereafter. The transported s is dimensionless, has zero initial/inlet values, and has a uniform +1 volumetric source. Do not omit its active evolution.

The following geometry, models and initial/boundary data define the task. Coordinates are in metres. Preserve vertex/block order, cell counts, grading and patch names for independently indexed output checks. You may choose linear solvers, relaxation and discretization schemes; these are not reference-matched. Cell-zone labels are bookkeeping, not an additional physics constraint. Use no larger initial time step or Courant limit than stated. Boundary value entries for wall functions, calculated conditions and outflow initial guesses are numerical initialization, not a new physical constraint.

```json
{
  "additional_equations": {
    "diffusivity": "nu + nut (default alphaD=alphaDt=1)",
    "enabled": true,
    "execute": "each time step",
    "field": "s",
    "reference_dictionary": {
      "enabled": "true",
      "field": "s",
      "fvOptions": {
        "unitySource": {
          "enabled": "true",
          "selectionMode": "all",
          "sources": {
            "s": "( 1 0 )"
          },
          "type": "scalarSemiImplicitSource",
          "volumeMode": "specific"
        }
      },
      "libs": "( solverFunctionObjects )",
      "resetOnStartUp": "false",
      "type": "scalarTransport",
      "write": "true",
      "writeControl": "writeTime",
      "writeInterval": "1"
    },
    "reset_on_startup": false,
    "source": "uniform explicit +1, implicit coefficient 0, volumeMode specific, all cells",
    "type": "scalarTransport",
    "write": "every field write"
  },
  "fields": {
    "U": {
      "boundaryField": {
        "defaultFaces": {
          "type": "noSlip"
        },
        "inlet": {
          "type": "pressureInletOutletVelocity",
          "value": "uniform ( 0 0 0 )"
        },
        "outlet1": {
          "inletValue": "uniform ( 0 0 0 )",
          "type": "inletOutlet",
          "value": "uniform ( 0 0 0 )"
        },
        "outlet2": {
          "inletValue": "uniform ( 0 0 0 )",
          "type": "inletOutlet",
          "value": "uniform ( 0 0 0 )"
        }
      },
      "dimensions": "[ 0 1 -1 0 0 0 0 ]",
      "internalField": "uniform ( 0 0 0 )"
    },
    "epsilon": {
      "boundaryField": {
        "defaultFaces": {
          "type": "epsilonWallFunction",
          "value": "uniform 200"
        },
        "inlet": {
          "mixingLength": "0.01",
          "type": "turbulentMixingLengthDissipationRateInlet",
          "value": "uniform 200"
        },
        "outlet1": {
          "inletValue": "uniform 200",
          "type": "inletOutlet"
        },
        "outlet2": {
          "inletValue": "uniform 200",
          "type": "inletOutlet"
        }
      },
      "dimensions": "[ 0 2 -3 0 0 0 0 ]",
      "internalField": "uniform 200"
    },
    "k": {
      "boundaryField": {
        "defaultFaces": {
          "type": "kqRWallFunction",
          "value": "uniform 0"
        },
        "inlet": {
          "intensity": "0.05",
          "type": "turbulentIntensityKineticEnergyInlet",
          "value": "uniform 0.2"
        },
        "outlet1": {
          "inletValue": "uniform 0.2",
          "type": "inletOutlet"
        },
        "outlet2": {
          "inletValue": "uniform 0.2",
          "type": "inletOutlet"
        }
      },
      "dimensions": "[ 0 2 -2 0 0 0 0 ]",
      "internalField": "uniform 0.2"
    },
    "nut": {
      "boundaryField": {
        "defaultFaces": {
          "type": "nutkWallFunction",
          "value": "uniform 0"
        },
        "inlet": {
          "type": "calculated",
          "value": "uniform 0"
        },
        "outlet1": {
          "type": "calculated",
          "value": "uniform 0"
        },
        "outlet2": {
          "type": "calculated",
          "value": "uniform 0"
        }
      },
      "dimensions": "[ 0 2 -1 0 0 0 0 ]",
      "internalField": "uniform 0"
    },
    "p": {
      "boundaryField": {
        "defaultFaces": {
          "type": "zeroGradient"
        },
        "inlet": {
          "p0": "table ( ( 0 10 ) ( 1 40 ) )",
          "type": "uniformTotalPressure"
        },
        "outlet1": {
          "type": "fixedValue",
          "value": "uniform 10"
        },
        "outlet2": {
          "type": "fixedValue",
          "value": "uniform 0"
        }
      },
      "dimensions": "[ 0 2 -2 0 0 0 0 ]",
      "internalField": "uniform 0"
    },
    "s": {
      "boundaryField": {
        "defaultFaces": {
          "type": "zeroGradient"
        },
        "inlet": {
          "type": "fixedValue",
          "value": "uniform 0"
        },
        "outlet1": {
          "inletValue": "uniform 0",
          "type": "inletOutlet"
        },
        "outlet2": {
          "inletValue": "uniform 0",
          "type": "inletOutlet"
        }
      },
      "dimensions": "[ 0 0 0 0 0 0 0 ]",
      "internalField": "uniform 0"
    }
  },
  "geometry": {
    "blocks": [
      {
        "cells": [
          50,
          5,
          5
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
          10,
          11,
          12,
          13
        ]
      },
      {
        "cells": [
          5,
          5,
          5
        ],
        "grading": [
          "1",
          "1",
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          1,
          4,
          5,
          2,
          11,
          14,
          15,
          12
        ]
      },
      {
        "cells": [
          5,
          50,
          5
        ],
        "grading": [
          "1",
          "1",
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          6,
          7,
          4,
          1,
          16,
          17,
          14,
          11
        ]
      },
      {
        "cells": [
          5,
          50,
          5
        ],
        "grading": [
          "1",
          "1",
          "1"
        ],
        "grading_kind": "simpleGrading",
        "vertices": [
          2,
          5,
          9,
          8,
          12,
          15,
          19,
          18
        ]
      }
    ],
    "cell_count": 3875,
    "edges": "( )",
    "merge_patch_pairs": "( )",
    "patches": {
      "defaultFaces": {
        "faces": "( )",
        "type": "wall"
      },
      "inlet": {
        "faces": "( ( 0 10 13 3 ) )",
        "type": "patch"
      },
      "outlet1": {
        "faces": "( ( 6 7 17 16 ) )",
        "type": "patch"
      },
      "outlet2": {
        "faces": "( ( 8 18 19 9 ) )",
        "type": "patch"
      }
    },
    "vertices_m": [
      [
        0.0,
        -0.01,
        0.0
      ],
      [
        0.2,
        -0.01,
        0.0
      ],
      [
        0.2,
        0.01,
        0.0
      ],
      [
        0.0,
        0.01,
        0.0
      ],
      [
        0.22,
        -0.01,
        0.0
      ],
      [
        0.22,
        0.01,
        0.0
      ],
      [
        0.2,
        -0.21,
        0.0
      ],
      [
        0.22,
        -0.21,
        0.0
      ],
      [
        0.2,
        0.21,
        0.0
      ],
      [
        0.22,
        0.21,
        0.0
      ],
      [
        0.0,
        -0.01,
        0.02
      ],
      [
        0.2,
        -0.01,
        0.02
      ],
      [
        0.2,
        0.01,
        0.02
      ],
      [
        0.0,
        0.01,
        0.02
      ],
      [
        0.22,
        -0.01,
        0.02
      ],
      [
        0.22,
        0.01,
        0.02
      ],
      [
        0.2,
        -0.21,
        0.02
      ],
      [
        0.22,
        -0.21,
        0.02
      ],
      [
        0.2,
        0.21,
        0.02
      ],
      [
        0.22,
        0.21,
        0.02
      ]
    ]
  },
  "models": {
    "custom_model_coefficients": false,
    "flow_model": "RAS/kEpsilon",
    "kinematic_viscosity_m2_s": 1e-05,
    "transport_model": "Newtonian"
  },
  "solver": "pimpleFoam",
  "time": {
    "adaptive": true,
    "early_convergence": false,
    "end": 1.5,
    "kind": "transient",
    "maximum_courant": 5.0,
    "maximum_initial_delta_t": 0.001,
    "start": 0.0
  }
}
```

Use ASCII, uncompressed output and write all active final fields. Do not submit a pre-generated mesh, a separate initial phi, moving-mesh physics, added momentum sources or custom model coefficients. Local bare dictionary references such as $p and $internalField are supported; environment/path expansion, dynamic code and arbitrary libraries/includes are not. Read-only probes are allowed. The scalarTransport function with the specified source must stay enabled; do not use -noFunctionObjects. 

Do not seek references, evaluator source, prior results, or external documentation.

[DRAFT: post-processing schema and independently qualified numeric acceptance are not released yet.]
