# Compressible flow after removal of a diaphragm

Create all required OpenFOAM v2306 inputs from scratch in /work. Only your own work and the public instructions are initially present.

At t=0 remove a diaphragm at x=0 in a one-dimensional inviscid ideal-gas tube. The tube is x=-5..5 m, y=-1..1 m, z=-1..1 m, with 100 x 1 x 1 uniform cells. Initially both sides are at rest. For x<0: p=100000 Pa and T=348.432 K. For x>=0: p=10000 Pa and T=278.746 K. The x-end faces have zero normal gradients; the four transverse faces use the OpenFOAM empty condition. Evolve to 0.007 s. Use perfectGas, Cp=1004.5 J/(kg K), molar mass 28.96 kg/kmol, Hf=2.544e6 J/kg, mu=0 and Pr=1 with sensible internal energy. Initialize the piecewise states with setFields; do not infer initial density independently of the equation of state. Pressure is absolute in Pa. Preserve the density, pressure, velocity and temperature waves.

Use rhoCentralFoam. Initial deltaT must be positive and no larger than 1e-06. Use adaptive time stepping with maxCo no larger than 0.2. Use ASCII, uncompressed final fields. Write the actual final time/iteration, not only earlier checkpoints.
Do not seek references, evaluator source, prior results, or external documentation.

## Execution protocol

Write system/science-action.json containing exactly {"action": "run", "solver": "rhoCentralFoam"} and finish this turn. A separate isolated OpenFOAM service snapshots your 0/, constant/, system/ files and runs this fixed workflow: [["mesh", "blockMesh"], ["initialize", "setFields"], ["mesh_check", "checkMesh"], ["solver", "rhoCentralFoam"]].
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
    "rho_cell_min_mean_max": {
      "unit": "kg/m3",
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
last_initial_residual and last_final_residual refer to the LAST Solving for rhoE line in the LAST Time block of solver.log (across both fluids for a multiregion task). These are diagnostic values, not pass thresholds. final_iteration is not a physical time in seconds.

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
    "offset": 0
  },
  "rho": {
    "relative_l2": 0.1,
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
| boundaryField.sides.type | zeroGradient |
| boundaryField.empty.type | empty |

### 0/U — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 1 -1 0 0 0 0 ] |
| boundaryField.sides.type | zeroGradient |
| boundaryField.empty.type | empty |

### 0/p — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 1 -1 -2 0 0 0 0 ] |
| boundaryField.sides.type | zeroGradient |
| boundaryField.empty.type | empty |

### constant/thermophysicalProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| thermoType.type | hePsiThermo |
| thermoType.mixture | pureMixture |
| thermoType.transport | const |
| thermoType.thermo | hConst |
| thermoType.equationOfState | perfectGas |
| thermoType.specie | specie |
| thermoType.energy | sensibleInternalEnergy |
| mixture.specie.molWeight | 28.96 |
| mixture.thermodynamics.Cp | 1004.5 |
| mixture.thermodynamics.Hf | 2.544e+06 |
| mixture.transport.mu | 0 |
| mixture.transport.Pr | 1 |

### constant/turbulenceProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| simulationType | laminar |

### system/blockMeshDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| scale | 1 |
| vertices | ( ( -5 -1 -1 ) ( 5 -1 -1 ) ( 5 1 -1 ) ( -5 1 -1 ) ( -5 -1 1 ) ( 5 -1 1 ) ( 5 1 1 ) ( -5 1 1 ) ) |
| blocks | ( hex ( 0 1 2 3 4 5 6 7 ) ( 100 1 1 ) simpleGrading ( 1 1 1 ) ) |
| edges | ( ) |
| boundary | ( sides { type patch ; faces ( ( 1 2 6 5 ) ( 0 4 7 3 ) ) ; } empty { type empty ; faces ( ( 0 1 5 4 ) ( 5 6 7 4 ) ( 3 7 6 2 ) ( 0 3 2 1 ) ) ; } ) |
| mergePatchPairs | ( ) |

### system/setFieldsDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| defaultFieldValues | ( volVectorFieldValue U ( 0 0 0 ) volScalarFieldValue T 348.432 volScalarFieldValue p 100000 ) |
| regions | ( boxToCell { box ( 0 -1 -1 ) ( 5 1 1 ) ; fieldValues ( volScalarFieldValue T 278.746 volScalarFieldValue p 10000 ) ; } ) |

