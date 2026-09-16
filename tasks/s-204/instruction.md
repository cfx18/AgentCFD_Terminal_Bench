# Natural convection in a closed three-dimensional cavity

Create all required OpenFOAM v2306 inputs from scratch in /work. Only your own work and the public instructions are initially present.

Compute natural convection of air in a sealed, fully three-dimensional cavity: x = 0..0.076 m, y = 0..2.18 m, z = -0.26..0.26 m. The x-max wall is held at 307.75 K, x-min at 288.15 K, and all remaining walls are adiabatic. All six walls are stationary no-slip walls. Gravity is (0,-9.81,0) m/s2. Initial temperature is 293 K and velocity is zero. Use a perfect-gas density law, RAS kOmegaSST turbulence, Cp = 1004.4 J/(kg K), molar mass 28.96 kg/kmol, dynamic viscosity 1.831e-5 Pa s, Pr = 0.705. Use the canonical 35 x 150 x 15 uniform cell ordering below. Run 1000 SIMPLE iterations or stop at the declared residual convergence criteria: p_rgh,U,h <= 1e-4 and k,omega <= 1e-3. The final 1000-iteration reference is a finite-iteration numerical state, not proof of a fully converged steady physical solution; report its actual residuals without claiming convergence.

Use buoyantSimpleFoam. Initial deltaT must be positive and no larger than 1. Use dimensionless deltaT=1 and steadyState ddt. Use ASCII, uncompressed final fields. Write the actual final time/iteration, not only earlier checkpoints.
Do not seek references, evaluator source, prior results, or external documentation.

## Execution protocol

Write system/science-action.json containing exactly {"action": "run", "solver": "buoyantSimpleFoam"} and finish this turn. A separate isolated OpenFOAM service snapshots your 0/, constant/, system/ files and runs this fixed workflow: [["mesh", "blockMesh"], ["mesh_check", "checkMesh"], ["solver", "buoyantSimpleFoam"]].
The solver is not installed in the agent workspace. Do not simulate success with a local script. No fixed failure-count cap is imposed; you can modify and resubmit using the remaining API and native budgets. Do not submit generated meshes, old time directories, shell scripts, custom shared libraries, coded functions, external includes or dynamic code. Standard submitted local text includes and dictionary macros are supported. You may use Python for your own postprocessor outside submitted input directories.

## Final report

After a successful run, read the real fields and sanitized solver log under /artifacts/<run_id>/. Replace the action file with this exact schema (zeros below are placeholders, not answers):

```json
{
  "action": "report",
  "run_id": "r-000001",
  "measurements": {
    "final_iteration": {
      "unit": "1",
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
      "unit": "Pa",
      "value": [
        0,
        0,
        0
      ]
    },
    "p_rgh_cell_min_mean_max": {
      "unit": "Pa",
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
    "omega_cell_min_mean_max": {
      "unit": "1/s",
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
    },
    "alphat_cell_min_mean_max": {
      "unit": "kg/(m s)",
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
last_initial_residual and last_final_residual refer to the LAST Solving for p_rgh line in the LAST Time block of solver.log (across both fluids for a multiregion task). These are diagnostic values, not pass thresholds. final_iteration is not a physical time in seconds.

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
  "p_rgh": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "T": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 293
  },
  "k": {
    "relative_l2": 0.25,
    "relative_linf": 0.5,
    "offset": 0
  },
  "omega": {
    "relative_l2": 0.25,
    "relative_linf": 0.5,
    "offset": 0
  },
  "nut": {
    "relative_l2": 0.25,
    "relative_linf": 0.5,
    "offset": 0
  },
  "alphat": {
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
| internalField | uniform 293 |
| boundaryField.frontAndBack.type | zeroGradient |
| boundaryField.topAndBottom.type | zeroGradient |
| boundaryField.hot.type | fixedValue |
| boundaryField.hot.value | uniform 307.75 |
| boundaryField.cold.type | fixedValue |
| boundaryField.cold.value | uniform 288.15 |

### 0/U — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 1 -1 0 0 0 0 ] |
| internalField | uniform ( 0 0 0 ) |
| boundaryField.frontAndBack.type | noSlip |
| boundaryField.topAndBottom.type | noSlip |
| boundaryField.hot.type | noSlip |
| boundaryField.cold.type | noSlip |

### 0/alphat — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 1 -1 -1 0 0 0 0 ] |
| internalField | uniform 0 |
| boundaryField.frontAndBack.type | compressible::alphatWallFunction |
| boundaryField.frontAndBack.Prt | 0.85 |
| boundaryField.frontAndBack.value | uniform 0 |
| boundaryField.topAndBottom.type | compressible::alphatWallFunction |
| boundaryField.topAndBottom.Prt | 0.85 |
| boundaryField.topAndBottom.value | uniform 0 |
| boundaryField.hot.type | compressible::alphatWallFunction |
| boundaryField.hot.Prt | 0.85 |
| boundaryField.hot.value | uniform 0 |
| boundaryField.cold.type | compressible::alphatWallFunction |
| boundaryField.cold.Prt | 0.85 |
| boundaryField.cold.value | uniform 0 |

### 0/k — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 2 -2 0 0 0 0 ] |
| internalField | uniform 3.75e-04 |
| boundaryField.frontAndBack.type | kqRWallFunction |
| boundaryField.frontAndBack.value | uniform 3.75e-04 |
| boundaryField.topAndBottom.type | kqRWallFunction |
| boundaryField.topAndBottom.value | uniform 3.75e-04 |
| boundaryField.hot.type | kqRWallFunction |
| boundaryField.hot.value | uniform 3.75e-04 |
| boundaryField.cold.type | kqRWallFunction |
| boundaryField.cold.value | uniform 3.75e-04 |

### 0/nut — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 2 -1 0 0 0 0 ] |
| internalField | uniform 0 |
| boundaryField.frontAndBack.type | nutUWallFunction |
| boundaryField.frontAndBack.value | uniform 0 |
| boundaryField.topAndBottom.type | nutUWallFunction |
| boundaryField.topAndBottom.value | uniform 0 |
| boundaryField.hot.type | nutUWallFunction |
| boundaryField.hot.value | uniform 0 |
| boundaryField.cold.type | nutUWallFunction |
| boundaryField.cold.value | uniform 0 |

### 0/omega — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 0 -1 0 0 0 0 ] |
| internalField | uniform 0.12 |
| boundaryField.frontAndBack.type | omegaWallFunction |
| boundaryField.frontAndBack.value | uniform 0.12 |
| boundaryField.topAndBottom.type | omegaWallFunction |
| boundaryField.topAndBottom.value | uniform 0.12 |
| boundaryField.hot.type | omegaWallFunction |
| boundaryField.hot.value | uniform 0.12 |
| boundaryField.cold.type | omegaWallFunction |
| boundaryField.cold.value | uniform 0.12 |

### 0/p — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 1 -1 -2 0 0 0 0 ] |
| internalField | uniform 1e5 |
| boundaryField.frontAndBack.type | calculated |
| boundaryField.frontAndBack.value | uniform 1e5 |
| boundaryField.topAndBottom.type | calculated |
| boundaryField.topAndBottom.value | uniform 1e5 |
| boundaryField.hot.type | calculated |
| boundaryField.hot.value | uniform 1e5 |
| boundaryField.cold.type | calculated |
| boundaryField.cold.value | uniform 1e5 |

### 0/p_rgh — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 1 -1 -2 0 0 0 0 ] |
| internalField | uniform 1e5 |
| boundaryField.frontAndBack.type | fixedFluxPressure |
| boundaryField.frontAndBack.value | uniform 1e5 |
| boundaryField.topAndBottom.type | fixedFluxPressure |
| boundaryField.topAndBottom.value | uniform 1e5 |
| boundaryField.hot.type | fixedFluxPressure |
| boundaryField.hot.value | uniform 1e5 |
| boundaryField.cold.type | fixedFluxPressure |
| boundaryField.cold.value | uniform 1e5 |

### constant/g — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 1 -2 0 0 0 0 ] |
| value | ( 0 -9.81 0 ) |

### constant/thermophysicalProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| thermoType.type | heRhoThermo |
| thermoType.mixture | pureMixture |
| thermoType.transport | const |
| thermoType.thermo | hConst |
| thermoType.equationOfState | perfectGas |
| thermoType.specie | specie |
| thermoType.energy | sensibleEnthalpy |
| mixture.specie.molWeight | 28.96 |
| mixture.thermodynamics.Cp | 1004.4 |
| mixture.thermodynamics.Hf | 0 |
| mixture.transport.mu | 1.831e-05 |
| mixture.transport.Pr | 0.705 |

### constant/turbulenceProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| simulationType | RAS |
| RAS.RASModel | kOmegaSST |
| RAS.turbulence | on |
| RAS.printCoeffs | on |

### system/blockMeshDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| scale | 0.001 |
| vertices | ( ( 0 0 -260 ) ( 76 0 -260 ) ( 76 2180 -260 ) ( 0 2180 -260 ) ( 0 0 260 ) ( 76 0 260 ) ( 76 2180 260 ) ( 0 2180 260 ) ) |
| edges | ( ) |
| blocks | ( hex ( 0 1 2 3 4 5 6 7 ) ( 35 150 15 ) simpleGrading ( 1 1 1 ) ) |
| boundary | ( frontAndBack { type wall ; faces ( ( 0 1 5 4 ) ( 2 3 7 6 ) ) ; } topAndBottom { type wall ; faces ( ( 4 5 6 7 ) ( 3 2 1 0 ) ) ; } hot { type wall ; faces ( ( 6 5 1 2 ) ) ; } cold { type wall ; faces ( ( 4 7 3 0 ) ) ; } ) |
| mergePatchPairs | ( ) |

