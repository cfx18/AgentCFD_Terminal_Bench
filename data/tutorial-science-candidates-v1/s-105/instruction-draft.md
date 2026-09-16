# Pressure-driven branching flow with a transported scalar and volume source

Build all OpenFOAM-v2306 input files from an empty workspace. No starter case is provided.

This is a three-dimensional duct, including no-slip front/back walls. outlet1 is at y=-0.21 m with kinematic pressure 10 m2/s2; outlet2 is at y=+0.21 m with pressure zero. Inlet total pressure is 10+30*t for 0<=t<=1 second and 40 thereafter. The transported s is dimensionless, has zero initial/inlet values, and has a uniform +1 volumetric source. Do not omit its active evolution.

The following geometry, models and initial/boundary data define the task. Coordinates are in metres. Preserve vertex/block order, cell counts, grading and patch names for independently indexed output checks. You may choose linear solvers, relaxation and discretization schemes; these are not reference-matched. Use no larger initial time step or Courant limit than stated. Boundary value entries for wall functions, calculated conditions and outflow initial guesses are numerical initialization, not a new physical constraint.

```json
{
  "solver": "pimpleFoam",
  "geometry": {
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
    ],
    "blocks": [
      {
        "vertices": [
          0,
          1,
          2,
          3,
          10,
          11,
          12,
          13
        ],
        "cells": [
          50,
          5,
          5
        ],
        "grading_kind": "simpleGrading",
        "grading": [
          "1",
          "1",
          "1"
        ]
      },
      {
        "vertices": [
          1,
          4,
          5,
          2,
          11,
          14,
          15,
          12
        ],
        "cells": [
          5,
          5,
          5
        ],
        "grading_kind": "simpleGrading",
        "grading": [
          "1",
          "1",
          "1"
        ]
      },
      {
        "vertices": [
          6,
          7,
          4,
          1,
          16,
          17,
          14,
          11
        ],
        "cells": [
          5,
          50,
          5
        ],
        "grading_kind": "simpleGrading",
        "grading": [
          "1",
          "1",
          "1"
        ]
      },
      {
        "vertices": [
          2,
          5,
          9,
          8,
          12,
          15,
          19,
          18
        ],
        "cells": [
          5,
          50,
          5
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
      "inlet": {
        "type": "patch",
        "faces": "( ( 0 10 13 3 ) )"
      },
      "outlet1": {
        "type": "patch",
        "faces": "( ( 6 7 17 16 ) )"
      },
      "outlet2": {
        "type": "patch",
        "faces": "( ( 8 18 19 9 ) )"
      },
      "defaultFaces": {
        "type": "wall",
        "faces": "( )"
      }
    },
    "edges": "( )",
    "merge_patch_pairs": "( )",
    "cell_count": 3875
  },
  "models": {
    "kinematic_viscosity_m2_s": 1e-05,
    "transport_model": "Newtonian",
    "flow_model": "RAS/kEpsilon",
    "custom_model_coefficients": false
  },
  "time": {
    "kind": "transient",
    "start": 0.0,
    "end": 1.5,
    "early_convergence": false,
    "maximum_initial_delta_t": 0.001,
    "adaptive": true,
    "maximum_courant": 5.0
  },
  "fields": {
    "U": {
      "dimensions": "[ 0 1 -1 0 0 0 0 ]",
      "internalField": "uniform ( 0 0 0 )",
      "boundaryField": {
        "inlet": {
          "type": "pressureInletOutletVelocity",
          "value": "uniform ( 0 0 0 )"
        },
        "outlet1": {
          "type": "inletOutlet",
          "inletValue": "uniform ( 0 0 0 )",
          "value": "uniform ( 0 0 0 )"
        },
        "outlet2": {
          "type": "inletOutlet",
          "inletValue": "uniform ( 0 0 0 )",
          "value": "uniform ( 0 0 0 )"
        },
        "defaultFaces": {
          "type": "noSlip"
        }
      }
    },
    "p": {
      "dimensions": "[ 0 2 -2 0 0 0 0 ]",
      "internalField": "uniform 0",
      "boundaryField": {
        "inlet": {
          "type": "uniformTotalPressure",
          "p0": "table ( ( 0 10 ) ( 1 40 ) )"
        },
        "outlet1": {
          "type": "fixedValue",
          "value": "uniform 10"
        },
        "outlet2": {
          "type": "fixedValue",
          "value": "uniform 0"
        },
        "defaultFaces": {
          "type": "zeroGradient"
        }
      }
    },
    "k": {
      "dimensions": "[ 0 2 -2 0 0 0 0 ]",
      "internalField": "uniform 0.2",
      "boundaryField": {
        "inlet": {
          "type": "turbulentIntensityKineticEnergyInlet",
          "intensity": "0.05",
          "value": "uniform 0.2"
        },
        "outlet1": {
          "type": "inletOutlet",
          "inletValue": "uniform 0.2"
        },
        "outlet2": {
          "type": "inletOutlet",
          "inletValue": "uniform 0.2"
        },
        "defaultFaces": {
          "type": "kqRWallFunction",
          "value": "uniform 0"
        }
      }
    },
    "epsilon": {
      "dimensions": "[ 0 2 -3 0 0 0 0 ]",
      "internalField": "uniform 200",
      "boundaryField": {
        "inlet": {
          "type": "turbulentMixingLengthDissipationRateInlet",
          "mixingLength": "0.01",
          "value": "uniform 200"
        },
        "outlet1": {
          "type": "inletOutlet",
          "inletValue": "uniform 200"
        },
        "outlet2": {
          "type": "inletOutlet",
          "inletValue": "uniform 200"
        },
        "defaultFaces": {
          "type": "epsilonWallFunction",
          "value": "uniform 200"
        }
      }
    },
    "nut": {
      "dimensions": "[ 0 2 -1 0 0 0 0 ]",
      "internalField": "uniform 0",
      "boundaryField": {
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
        },
        "defaultFaces": {
          "type": "nutkWallFunction",
          "value": "uniform 0"
        }
      }
    },
    "s": {
      "dimensions": "[ 0 0 0 0 0 0 0 ]",
      "internalField": "uniform 0",
      "boundaryField": {
        "inlet": {
          "type": "fixedValue",
          "value": "uniform 0"
        },
        "outlet1": {
          "type": "inletOutlet",
          "inletValue": "uniform 0"
        },
        "outlet2": {
          "type": "inletOutlet",
          "inletValue": "uniform 0"
        },
        "defaultFaces": {
          "type": "zeroGradient"
        }
      }
    }
  },
  "additional_equations": {
    "type": "scalarTransport",
    "field": "s",
    "enabled": true,
    "diffusivity": "nu + nut (default alphaD=alphaDt=1)",
    "source": "uniform explicit +1, implicit coefficient 0, volumeMode specific, all cells",
    "reset_on_startup": false,
    "execute": "each time step",
    "write": "every field write",
    "reference_dictionary": {
      "type": "scalarTransport",
      "libs": "( solverFunctionObjects )",
      "enabled": "true",
      "writeControl": "writeTime",
      "writeInterval": "1",
      "field": "s",
      "write": "true",
      "fvOptions": {
        "unitySource": {
          "type": "scalarSemiImplicitSource",
          "enabled": "true",
          "selectionMode": "all",
          "volumeMode": "specific",
          "sources": {
            "s": "( 1 0 )"
          }
        }
      },
      "resetOnStartUp": "false"
    }
  }
}
```

Use ASCII, uncompressed output and write all active final fields. Do not submit a pre-generated mesh, a separate initial phi, moving-mesh physics, added momentum sources or custom model coefficients. Local bare dictionary references such as $p and $internalField are supported; environment/path expansion, dynamic code and arbitrary libraries/includes are not. Read-only probes are allowed. The scalarTransport function with the specified source must stay enabled; do not use -noFunctionObjects. 

Do not seek references, evaluator source, prior results, or external documentation.

[DRAFT: post-processing schema and independently qualified numeric acceptance are not released yet.]
