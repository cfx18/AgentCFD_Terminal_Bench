# Pressure-driven branching flow with temperature-dependent viscosity

Create all required OpenFOAM v2306 inputs from scratch in /work. Only your own work and the public instructions are initially present.

Construct a pressure-driven, three-dimensional branching duct with the geometry and boundary data below. Use RAS kEpsilon turbulence. The transport law is ArrheniusBirdCarreau with nu0 = nuInf = 15e-6 m2/s, k = 0 s, n = 1, alpha = 0.1 K^-1, and Talpha = 300 K. Interpret this parameter combination physically; retain all nonzero physical dependencies. Initially T = 300 K and the inlet temperature is 315 K. Solve the temperature energy balance using Cp = 1000 J/(kg K), thermal conductivity 0.0257 W/(m K), density 1.2 kg/m3, including viscous dissipation. Evolve to 1.5 s. Pressure here is kinematic, in m2/s2. Use the standard energyTransport implementation and retain the temperature-viscosity coupling.

Use pimpleFoam. Initial deltaT must be positive and no larger than 0.001. Use adaptive time stepping with maxCo no larger than 5. Use ASCII, uncompressed final fields. Write the actual final time/iteration, not only earlier checkpoints.
Do not seek references, evaluator source, prior results, or external documentation.

## Execution protocol

Write system/science-action.json containing exactly {"action": "run", "solver": "pimpleFoam"} and finish this turn. A separate isolated OpenFOAM service snapshots your 0/, constant/, system/ files and runs this fixed workflow: [["mesh", "blockMesh"], ["mesh_check", "checkMesh"], ["solver", "pimpleFoam"]].
The solver is not installed in the agent workspace. Do not simulate success with a local script. No fixed failure-count cap is imposed; you can modify and resubmit using the remaining API and native budgets. Do not submit generated meshes, old time directories, shell scripts, custom shared libraries, coded functions, external includes or dynamic code. Standard submitted local text includes and dictionary macros are supported. You may use Python for your own postprocessor outside submitted input directories.

## Final report

After a successful run, read the real fields and sanitized solver log under /artifacts/<run_id>/. Replace the action file with this exact schema (zeros below are placeholders, not answers):

```json
{
  "action": "report",
  "run_id": "r-000001",
  "measurements": {
    "final_time": {
      "unit": "s",
      "value": 0
    },
    "last_initial_residual": {
      "unit": "1",
      "value": 0
    },
    "last_final_residual": {
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
    "U_speed_rms": {
      "unit": "m/s",
      "value": 0
    },
    "U_speed_max": {
      "unit": "m/s",
      "value": 0
    },
    "p_cell_min_mean_max": {
      "unit": "m2/s2",
      "value": [
        0,
        0,
        0
      ]
    },
    "T_cell_min_mean_max": {
      "unit": "K",
      "value": [
        0,
        0,
        0
      ]
    },
    "k_cell_min_mean_max": {
      "unit": "m2/s2",
      "value": [
        0,
        0,
        0
      ]
    },
    "epsilon_cell_min_mean_max": {
      "unit": "m2/s3",
      "value": [
        0,
        0,
        0
      ]
    },
    "nut_cell_min_mean_max": {
      "unit": "m2/s",
      "value": [
        0,
        0,
        0
      ]
    }
  }
}
```

For each scalar report [minimum, arithmetic mean, maximum] of all INTERNAL cell values at the final step. For U report [mean(Ux),mean(Uy),mean(Uz)], RMS speed=sqrt(mean(Ux^2+Uy^2+Uz^2)), and maximum speed. Statistics are unweighted by cell volume. Regional metric names use region_field; the underlying files are time/region/field. Scalars without a region use time/field. Respect the units in the schema.
last_initial_residual and last_final_residual refer to the LAST Solving for p line in the LAST Time block of solver.log (across both fluids for a multiregion task). These are diagnostic values, not pass thresholds. final_iteration is not a physical time in seconds.

## Acceptance

Physical geometry, canonical cell ordering, materials, initial/boundary data and active equations must hold. Discretization and linear-solver dictionaries need not match a reference. Native completion is necessary but not sufficient. The verifier independently re-extracts the requested metrics (report tolerance 1e-6 absolute + 1e-5 relative) and compares ALL final internal fields to a hidden executed original on the prescribed discretization. This is a finite-resolution numerical reproduction pilot, not an experimental validation or independent heat-flux/energy-conservation certification.
For each field, relative L2=RMS(observed-reference)/max(RMS(reference-offset),1e-12); relative Linf=max(abs(observed-reference))/max(max(abs(reference-offset)),1e-12). Flatten velocity xyz components before comparison. Offsets below avoid normalizing small temperature changes by an irrelevant absolute 300 K scale. All limits are frozen before model evaluation:

```json
{
  "U": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "p": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "T": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 300
  },
  "k": {
    "relative_l2": 0.25,
    "relative_linf": 0.5,
    "offset": 0
  },
  "epsilon": {
    "relative_l2": 0.25,
    "relative_linf": 0.5,
    "offset": 0
  },
  "nut": {
    "relative_l2": 0.25,
    "relative_linf": 0.5,
    "offset": 0
  }
}
```

Native feedback contains logs and public check outcomes, not hidden references or expected numbers. Nonnegative turbulence quantities and positive absolute temperatures, densities and absolute pressures are required. Do not fabricate any reported field or residual.

## Physical and canonical mesh parameter sheet

This sheet fixes the physical inputs and cell layout; it does not supply numerical solver dictionaries. Boundary-law implementation names identify the intended laws. Equivalent no-slip forms are accepted. An unlisted change to the physical setup is not a repair of a numerical problem.

### 0/T — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 0 0 1 0 0 0 ] |
| internalField | uniform 300 |
| boundaryField.inlet.type | fixedValue |
| boundaryField.inlet.value | uniform 315 |
| boundaryField.outlet1.type | inletOutlet |
| boundaryField.outlet1.inletValue | uniform 300 |
| boundaryField.outlet2.type | inletOutlet |
| boundaryField.outlet2.inletValue | uniform 300 |
| boundaryField.defaultFaces.type | zeroGradient |

### 0/U — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 1 -1 0 0 0 0 ] |
| internalField | uniform ( 0 0 0 ) |
| boundaryField.inlet.type | pressureInletOutletVelocity |
| boundaryField.inlet.value | uniform ( 0 0 0 ) |
| boundaryField.outlet1.type | inletOutlet |
| boundaryField.outlet1.inletValue | uniform ( 0 0 0 ) |
| boundaryField.outlet1.value | uniform ( 0 0 0 ) |
| boundaryField.outlet2.type | inletOutlet |
| boundaryField.outlet2.inletValue | uniform ( 0 0 0 ) |
| boundaryField.outlet2.value | uniform ( 0 0 0 ) |
| boundaryField.defaultFaces.type | noSlip |

### 0/epsilon — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 2 -3 0 0 0 0 ] |
| internalField | uniform 200 |
| boundaryField.inlet.type | turbulentMixingLengthDissipationRateInlet |
| boundaryField.inlet.mixingLength | 0.01 |
| boundaryField.inlet.value | uniform 200 |
| boundaryField.outlet1.type | inletOutlet |
| boundaryField.outlet1.inletValue | uniform 200 |
| boundaryField.outlet2.type | inletOutlet |
| boundaryField.outlet2.inletValue | uniform 200 |
| boundaryField.defaultFaces.type | epsilonWallFunction |
| boundaryField.defaultFaces.value | uniform 200 |

### 0/k — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 2 -2 0 0 0 0 ] |
| internalField | uniform 0.2 |
| boundaryField.inlet.type | turbulentIntensityKineticEnergyInlet |
| boundaryField.inlet.intensity | 0.05 |
| boundaryField.inlet.value | uniform 0.2 |
| boundaryField.outlet1.type | inletOutlet |
| boundaryField.outlet1.inletValue | uniform 0.2 |
| boundaryField.outlet2.type | inletOutlet |
| boundaryField.outlet2.inletValue | uniform 0.2 |
| boundaryField.defaultFaces.type | kqRWallFunction |
| boundaryField.defaultFaces.value | uniform 0 |

### 0/nut — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 2 -1 0 0 0 0 ] |
| internalField | uniform 0 |
| boundaryField.inlet.type | calculated |
| boundaryField.inlet.value | uniform 0 |
| boundaryField.outlet1.type | calculated |
| boundaryField.outlet1.value | uniform 0 |
| boundaryField.outlet2.type | calculated |
| boundaryField.outlet2.value | uniform 0 |
| boundaryField.defaultFaces.type | nutkWallFunction |
| boundaryField.defaultFaces.value | uniform 0 |

### 0/p — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 2 -2 0 0 0 0 ] |
| internalField | uniform 0 |
| boundaryField.inlet.type | uniformTotalPressure |
| boundaryField.inlet.p0 | table ( ( 0 10 ) ( 1 40 ) ) |
| boundaryField.outlet1.type | fixedValue |
| boundaryField.outlet1.value | uniform 10 |
| boundaryField.outlet2.type | fixedValue |
| boundaryField.outlet2.value | uniform 0 |
| boundaryField.defaultFaces.type | zeroGradient |

### constant/transportProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| transportModel | ArrheniusBirdCarreau |
| alpha | 0.1 |
| Talpha | 300 |
| nu0 | 15e-06 |
| nuInf | 15e-06 |
| k | 0 |
| n | 1 |

### constant/turbulenceProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| simulationType | RAS |
| RAS.RASModel | kEpsilon |
| RAS.turbulence | on |
| RAS.printCoeffs | on |

### system/blockMeshDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| scale | 1 |
| vertices | ( ( 0.0 -0.01 0 ) ( 0.2 -0.01 0 ) ( 0.2 0.01 0 ) ( 0.0 0.01 0 ) ( 0.22 -0.01 0 ) ( 0.22 0.01 0 ) ( 0.2 -0.21 0 ) ( 0.22 -0.21 0 ) ( 0.2 0.21 0 ) ( 0.22 0.21 0 ) ( 0.0 -0.01 0.02 ) ( 0.2 -0.01 0.02 ) ( 0.2 0.01 0.02 ) ( 0.0 0.01 0.02 ) ( 0.22 -0.01 0.02 ) ( 0.22 0.01 0.02 ) ( 0.2 -0.21 0.02 ) ( 0.22 -0.21 0.02 ) ( 0.2 0.21 0.02 ) ( 0.22 0.21 0.02 ) ) |
| blocks | ( hex ( 0 1 2 3 10 11 12 13 ) ( 50 5 5 ) simpleGrading ( 1 1 1 ) hex ( 1 4 5 2 11 14 15 12 ) ( 5 5 5 ) simpleGrading ( 1 1 1 ) hex ( 6 7 4 1 16 17 14 11 ) ( 5 50 5 ) simpleGrading ( 1 1 1 ) hex ( 2 5 9 8 12 15 19 18 ) ( 5 50 5 ) simpleGrading ( 1 1 1 ) ) |
| edges | ( ) |
| boundary | ( inlet { type patch ; faces ( ( 0 10 13 3 ) ) ; } outlet1 { type patch ; faces ( ( 6 7 17 16 ) ) ; } outlet2 { type patch ; faces ( ( 8 18 19 9 ) ) ; } defaultFaces { type wall ; faces ( ) ; } ) |
| mergePatchPairs | ( ) |

