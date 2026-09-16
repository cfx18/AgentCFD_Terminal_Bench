# Transient conjugate heat transfer through a resistive contact

Create all required OpenFOAM v2306 inputs from scratch in /work. Only your own work and the public instructions are initially present.

Build a five-region conjugate heat-transfer model. Water and air occupy the two fluid regions; the other three regions conduct heat as solids. All regions initially have temperature 300 K. The heater base minY is maintained at 500 K, NOT supplied with a fixed 500 W heat rate. Between heater and leftSolid, a layer 0.001 m thick with conductivity 0.0005 W/(m K) provides thermal contact resistance. Other fluid-solid contacts are perfect thermal contacts. Treat radiation as disabled. Evolve to 100 s; this is transient, so do not assume zero energy storage. Use the named regions and the exact cell-selection geometry specified below. Create global 0/ fields, then per-region changeDictionaryDict files; the service splits cell zones and applies these dictionaries.

Use chtMultiRegionFoam. Initial deltaT must be positive and no larger than 0.001. Use adaptive time stepping with maxCo no larger than 0.6. Use ASCII, uncompressed final fields. Write the actual final time/iteration, not only earlier checkpoints.
Do not seek references, evaluator source, prior results, or external documentation.

## Execution protocol

Write system/science-action.json containing exactly {"action": "run", "solver": "chtMultiRegionFoam"} and finish this turn. A separate isolated OpenFOAM service snapshots your 0/, constant/, system/ files and runs this fixed workflow: [["mesh", "blockMesh"], ["zones", "topoSet"], ["split", "splitMeshRegions", "-cellZones", "-overwrite"], ["boundary_bottomwater", "changeDictionary", "-region", "bottomWater"], ["boundary_topair", "changeDictionary", "-region", "topAir"], ["boundary_heater", "changeDictionary", "-region", "heater"], ["boundary_leftsolid", "changeDictionary", "-region", "leftSolid"], ["boundary_rightsolid", "changeDictionary", "-region", "rightSolid"], ["mesh_check", "checkMesh", "-allRegions"], ["solver", "chtMultiRegionFoam"]].
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
    "bottomWater_T_cell_min_mean_max": {
      "unit": "K",
      "value": [
        0,
        0,
        0
      ]
    },
    "bottomWater_U_cell_mean": {
      "unit": "m/s",
      "value": [
        0,
        0,
        0
      ]
    },
    "bottomWater_U_speed_rms": {
      "unit": "m/s",
      "value": 0
    },
    "bottomWater_U_speed_max": {
      "unit": "m/s",
      "value": 0
    },
    "bottomWater_p_cell_min_mean_max": {
      "unit": "Pa",
      "value": [
        0,
        0,
        0
      ]
    },
    "bottomWater_p_rgh_cell_min_mean_max": {
      "unit": "Pa",
      "value": [
        0,
        0,
        0
      ]
    },
    "topAir_T_cell_min_mean_max": {
      "unit": "K",
      "value": [
        0,
        0,
        0
      ]
    },
    "topAir_U_cell_mean": {
      "unit": "m/s",
      "value": [
        0,
        0,
        0
      ]
    },
    "topAir_U_speed_rms": {
      "unit": "m/s",
      "value": 0
    },
    "topAir_U_speed_max": {
      "unit": "m/s",
      "value": 0
    },
    "topAir_p_cell_min_mean_max": {
      "unit": "Pa",
      "value": [
        0,
        0,
        0
      ]
    },
    "topAir_p_rgh_cell_min_mean_max": {
      "unit": "Pa",
      "value": [
        0,
        0,
        0
      ]
    },
    "heater_T_cell_min_mean_max": {
      "unit": "K",
      "value": [
        0,
        0,
        0
      ]
    },
    "leftSolid_T_cell_min_mean_max": {
      "unit": "K",
      "value": [
        0,
        0,
        0
      ]
    },
    "rightSolid_T_cell_min_mean_max": {
      "unit": "K",
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
  "bottomWater/T": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 300
  },
  "bottomWater/U": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "bottomWater/p": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "bottomWater/p_rgh": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "topAir/T": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 300
  },
  "topAir/U": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "topAir/p": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "topAir/p_rgh": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 0
  },
  "heater/T": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 300
  },
  "leftSolid/T": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 300
  },
  "rightSolid/T": {
    "relative_l2": 0.1,
    "relative_linf": 0.5,
    "offset": 300
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
| boundaryField.".*".type | calculated |
| boundaryField.".*".value | uniform 300 |

### 0/U — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 1 -1 0 0 0 0 ] |
| internalField | uniform ( 0.01 0 0 ) |
| boundaryField.".*".type | calculated |
| boundaryField.".*".value | uniform ( 0.01 0 0 ) |

### 0/p — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 1 -1 -2 0 0 0 0 ] |
| internalField | uniform 1e5 |
| boundaryField.".*".type | calculated |
| boundaryField.".*".value | uniform 1e5 |

### 0/p_rgh — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 1 -1 -2 0 0 0 0 ] |
| internalField | uniform 1e5 |
| boundaryField.".*".type | calculated |
| boundaryField.".*".value | uniform 1e5 |

### constant/bottomWater/radiationProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| radiation | off |
| radiationModel | none |

### constant/bottomWater/thermophysicalProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| thermoType.type | heRhoThermo |
| thermoType.mixture | pureMixture |
| thermoType.transport | const |
| thermoType.thermo | hConst |
| thermoType.equationOfState | rhoConst |
| thermoType.specie | specie |
| thermoType.energy | sensibleEnthalpy |
| mixture.specie.molWeight | 18 |
| mixture.equationOfState.rho | 1000 |
| mixture.thermodynamics.Cp | 4181 |
| mixture.thermodynamics.Hf | 0 |
| mixture.transport.mu | 959e-6 |
| mixture.transport.Pr | 6.62 |

### constant/bottomWater/turbulenceProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| simulationType | laminar |

### constant/g — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| dimensions | [ 0 1 -2 0 0 0 0 ] |
| value | ( 0 -9.81 0 ) |

### constant/heater/radiationProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| radiation | off |
| radiationModel | none |

### constant/heater/thermophysicalProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| thermoType.type | heSolidThermo |
| thermoType.mixture | pureMixture |
| thermoType.transport | constIso |
| thermoType.thermo | hConst |
| thermoType.equationOfState | rhoConst |
| thermoType.specie | specie |
| thermoType.energy | sensibleEnthalpy |
| mixture.specie.molWeight | 50 |
| mixture.transport.kappa | 80 |
| mixture.thermodynamics.Hf | 0 |
| mixture.thermodynamics.Cp | 450 |
| mixture.equationOfState.rho | 8000 |

### constant/leftSolid/radiationProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| radiation | off |
| radiationModel | none |

### constant/leftSolid/thermophysicalProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| thermoType.type | heSolidThermo |
| thermoType.mixture | pureMixture |
| thermoType.transport | constIso |
| thermoType.thermo | hConst |
| thermoType.equationOfState | rhoConst |
| thermoType.specie | specie |
| thermoType.energy | sensibleEnthalpy |
| mixture.specie.molWeight | 50 |
| mixture.transport.kappa | 80 |
| mixture.thermodynamics.Hf | 0 |
| mixture.thermodynamics.Cp | 450 |
| mixture.equationOfState.rho | 8000 |

### constant/regionProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| regions | ( fluid ( bottomWater topAir ) solid ( heater leftSolid rightSolid ) ) |

### constant/rightSolid/radiationProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| radiation | off |
| radiationModel | none |

### constant/rightSolid/thermophysicalProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| thermoType.type | heSolidThermo |
| thermoType.mixture | pureMixture |
| thermoType.transport | constIso |
| thermoType.thermo | hConst |
| thermoType.equationOfState | rhoConst |
| thermoType.specie | specie |
| thermoType.energy | sensibleEnthalpy |
| mixture.specie.molWeight | 50 |
| mixture.transport.kappa | 80 |
| mixture.thermodynamics.Hf | 0 |
| mixture.thermodynamics.Cp | 450 |
| mixture.equationOfState.rho | 8000 |

### constant/topAir/radiationProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| radiation | off |
| radiationModel | none |

### constant/topAir/thermophysicalProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| thermoType.type | heRhoThermo |
| thermoType.mixture | pureMixture |
| thermoType.transport | const |
| thermoType.thermo | hConst |
| thermoType.equationOfState | perfectGas |
| thermoType.specie | specie |
| thermoType.energy | sensibleEnthalpy |
| mixture.specie.molWeight | 28.9 |
| mixture.thermodynamics.Cp | 1000 |
| mixture.thermodynamics.Hf | 0 |
| mixture.transport.mu | 1.8e-05 |
| mixture.transport.Pr | 0.7 |

### constant/topAir/turbulenceProperties — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| simulationType | laminar |

### system/blockMeshDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| scale | 1 |
| vertices | ( ( -0.1 -0.04 -0.05 ) ( 0.1 -0.04 -0.05 ) ( 0.1 0.04 -0.05 ) ( -0.1 0.04 -0.05 ) ( -0.1 -0.04 0.05 ) ( 0.1 -0.04 0.05 ) ( 0.1 0.04 0.05 ) ( -0.1 0.04 0.05 ) ) |
| blocks | ( hex ( 0 1 2 3 4 5 6 7 ) ( 30 10 10 ) simpleGrading ( 1 1 1 ) ) |
| edges | ( ) |
| boundary | ( maxY { type wall ; faces ( ( 3 7 6 2 ) ) ; } minX { type patch ; faces ( ( 0 4 7 3 ) ) ; } maxX { type patch ; faces ( ( 2 6 5 1 ) ) ; } minY { type wall ; faces ( ( 1 5 4 0 ) ) ; } minZ { type wall ; faces ( ( 0 3 2 1 ) ) ; } maxZ { type wall ; faces ( ( 4 5 6 7 ) ) ; } ) |
| mergePatchPairs | ( ) |

### system/bottomWater/changeDictionaryDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| U.internalField | uniform ( 0.001 0 0 ) |
| U.boundaryField.minX.type | fixedValue |
| U.boundaryField.minX.value | uniform ( 0.001 0 0 ) |
| U.boundaryField.maxX.type | inletOutlet |
| U.boundaryField.maxX.inletValue | uniform ( 0 0 0 ) |
| U.boundaryField.".*".type | fixedValue |
| U.boundaryField.".*".value | uniform ( 0 0 0 ) |
| T.internalField | uniform 300 |
| T.boundaryField.minX.type | fixedValue |
| T.boundaryField.minX.value | uniform 300 |
| T.boundaryField.maxX.type | inletOutlet |
| T.boundaryField.maxX.inletValue | uniform 300 |
| T.boundaryField.".*".type | zeroGradient |
| T.boundaryField.".*".value | uniform 300 |
| T.boundaryField."bottomWater_to_.*".type | compressible::turbulentTemperatureRadCoupledMixed |
| T.boundaryField."bottomWater_to_.*".Tnbr | T |
| T.boundaryField."bottomWater_to_.*".kappaMethod | fluidThermo |
| T.boundaryField."bottomWater_to_.*".value | uniform 300 |
| epsilon.internalField | uniform 0.01 |
| epsilon.boundaryField.minX.type | fixedValue |
| epsilon.boundaryField.minX.value | uniform 0.01 |
| epsilon.boundaryField.maxX.type | inletOutlet |
| epsilon.boundaryField.maxX.inletValue | uniform 0.01 |
| epsilon.boundaryField.".*".type | epsilonWallFunction |
| epsilon.boundaryField.".*".value | uniform 0.01 |
| k.internalField | uniform 0.1 |
| k.boundaryField.minX.type | inletOutlet |
| k.boundaryField.minX.inletValue | uniform 0.1 |
| k.boundaryField.maxX.type | zeroGradient |
| k.boundaryField.maxX.value | uniform 0.1 |
| k.boundaryField.".*".type | kqRWallFunction |
| k.boundaryField.".*".value | uniform 0.1 |
| p_rgh.internalField | uniform 0 |
| p_rgh.boundaryField.minX.type | zeroGradient |
| p_rgh.boundaryField.minX.value | uniform 0 |
| p_rgh.boundaryField.maxX.type | fixedValue |
| p_rgh.boundaryField.maxX.value | uniform 0 |
| p_rgh.boundaryField.".*".type | fixedFluxPressure |
| p_rgh.boundaryField.".*".value | uniform 0 |
| p.internalField | uniform 0 |
| p.boundaryField.".*".type | calculated |
| p.boundaryField.".*".value | uniform 0 |

### system/heater/changeDictionaryDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| boundary.minY.type | patch |
| boundary.minY.inGroups | ( coupleGroup ) |
| boundary.minZ.type | patch |
| boundary.maxZ.type | patch |
| T.internalField | uniform 300 |
| T.boundaryField.".*".type | zeroGradient |
| T.boundaryField.".*".value | uniform 300 |
| T.boundaryField."heater_to_.*".type | compressible::turbulentTemperatureRadCoupledMixed |
| T.boundaryField."heater_to_.*".Tnbr | T |
| T.boundaryField."heater_to_.*".kappaMethod | solidThermo |
| T.boundaryField."heater_to_.*".value | uniform 300 |
| T.boundaryField.heater_to_leftSolid.type | compressible::turbulentTemperatureRadCoupledMixed |
| T.boundaryField.heater_to_leftSolid.Tnbr | T |
| T.boundaryField.heater_to_leftSolid.kappaMethod | solidThermo |
| T.boundaryField.heater_to_leftSolid.thicknessLayers | ( 1e-3 ) |
| T.boundaryField.heater_to_leftSolid.kappaLayers | ( 5e-4 ) |
| T.boundaryField.heater_to_leftSolid.value | uniform 300 |
| T.boundaryField.minY.type | fixedValue |
| T.boundaryField.minY.value | uniform 500 |

### system/leftSolid/changeDictionaryDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| boundary.minZ.type | patch |
| boundary.maxZ.type | patch |
| T.internalField | uniform 300 |
| T.boundaryField.".*".type | zeroGradient |
| T.boundaryField.".*".value | uniform 300 |
| T.boundaryField."leftSolid_to_.*".type | compressible::turbulentTemperatureRadCoupledMixed |
| T.boundaryField."leftSolid_to_.*".Tnbr | T |
| T.boundaryField."leftSolid_to_.*".kappaMethod | solidThermo |
| T.boundaryField."leftSolid_to_.*".value | uniform 300 |
| T.boundaryField.leftSolid_to_heater.type | compressible::turbulentTemperatureRadCoupledMixed |
| T.boundaryField.leftSolid_to_heater.Tnbr | T |
| T.boundaryField.leftSolid_to_heater.kappaMethod | solidThermo |
| T.boundaryField.leftSolid_to_heater.thicknessLayers | ( 1e-3 ) |
| T.boundaryField.leftSolid_to_heater.kappaLayers | ( 5e-4 ) |
| T.boundaryField.leftSolid_to_heater.value | uniform 300 |

### system/rightSolid/changeDictionaryDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| boundary.minZ.type | patch |
| boundary.maxZ.type | patch |
| T.internalField | uniform 300 |
| T.boundaryField.".*".type | zeroGradient |
| T.boundaryField.".*".value | uniform 300 |
| T.boundaryField."rightSolid_to_.*".type | compressible::turbulentTemperatureRadCoupledMixed |
| T.boundaryField."rightSolid_to_.*".Tnbr | T |
| T.boundaryField."rightSolid_to_.*".kappaMethod | solidThermo |
| T.boundaryField."rightSolid_to_.*".value | uniform 300 |

### system/topAir/changeDictionaryDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| boundary.minX.inGroups | ( coupleGroup ) |
| U.internalField | uniform ( 0.1 0 0 ) |
| U.boundaryField.".*".type | fixedValue |
| U.boundaryField.".*".value | uniform ( 0 0 0 ) |
| U.boundaryField.minX.type | fixedValue |
| U.boundaryField.minX.value | uniform ( 0.1 0 0 ) |
| U.boundaryField.maxX.type | inletOutlet |
| U.boundaryField.maxX.inletValue | uniform ( 0 0 0 ) |
| U.boundaryField.maxX.value | uniform ( 0.1 0 0 ) |
| T.internalField | uniform 300 |
| T.boundaryField.".*".type | zeroGradient |
| T.boundaryField.minX.type | fixedValue |
| T.boundaryField.minX.value | uniform 300 |
| T.boundaryField.maxX.type | inletOutlet |
| T.boundaryField.maxX.inletValue | uniform 300 |
| T.boundaryField.maxX.value | uniform 300 |
| T.boundaryField."topAir_to_.*".type | compressible::turbulentTemperatureRadCoupledMixed |
| T.boundaryField."topAir_to_.*".Tnbr | T |
| T.boundaryField."topAir_to_.*".kappaMethod | fluidThermo |
| T.boundaryField."topAir_to_.*".value | uniform 300 |
| epsilon.internalField | uniform 0.01 |
| epsilon.boundaryField.".*".type | epsilonWallFunction |
| epsilon.boundaryField.".*".value | uniform 0.01 |
| epsilon.boundaryField.minX.type | fixedValue |
| epsilon.boundaryField.minX.value | uniform 0.01 |
| epsilon.boundaryField.maxX.type | inletOutlet |
| epsilon.boundaryField.maxX.inletValue | uniform 0.01 |
| epsilon.boundaryField.maxX.value | uniform 0.01 |
| k.internalField | uniform 0.1 |
| k.boundaryField.".*".type | kqRWallFunction |
| k.boundaryField.".*".value | uniform 0.1 |
| k.boundaryField.minX.type | fixedValue |
| k.boundaryField.minX.value | uniform 0.1 |
| k.boundaryField.maxX.type | inletOutlet |
| k.boundaryField.maxX.inletValue | uniform 0.1 |
| k.boundaryField.maxX.value | uniform 0.1 |
| p_rgh.internalField | uniform 1e5 |
| p_rgh.boundaryField.".*".type | fixedFluxPressure |
| p_rgh.boundaryField.".*".value | uniform 1e5 |
| p_rgh.boundaryField.maxX.type | fixedValue |
| p_rgh.boundaryField.maxX.value | uniform 1e5 |
| p.internalField | uniform 1e5 |
| p.boundaryField.".*".type | calculated |
| p.boundaryField.".*".value | uniform 1e5 |
| p.boundaryField.maxX.type | calculated |
| p.boundaryField.maxX.value | uniform 1e5 |

### system/topoSetDict — physical specification

| Quantity / boundary | Required value or law |
|---|---|
| actions | ( { name heaterCellSet ; type cellSet ; action new ; source boxToCell ; box ( -0.01001 0 -100 ) ( 0.01001 0.00999 100 ) ; } { name heaterCellSet ; type cellSet ; action add ; source boxToCell ; box ( -0.01001 -100 -0.01001 ) ( 0.01001 0.00999 0.01001 ) ; } { name heater ; type cellZoneSet ; action new ; source setToCellZone ; set heaterCellSet ; } { name leftSolidCellSet ; type cellSet ; action new ; source boxToCell ; box ( -100 0 -100 ) ( -0.01001 0.00999 100 ) ; } { name leftSolid ; type cellZoneSet ; action new ; source setToCellZone ; set leftSolidCellSet ; } { name rightSolidCellSet ; type cellSet ; action new ; source boxToCell ; box ( 0.01001 0 -100 ) ( 100 0.00999 100 ) ; } { name rightSolid ; type cellZoneSet ; action new ; source setToCellZone ; set rightSolidCellSet ; } { name topAirCellSet ; type cellSet ; action new ; source boxToCell ; box ( -100 0.00999 -100 ) ( 100 100 100 ) ; } { name topAir ; type cellZoneSet ; action new ; source setToCellZone ; set topAirCellSet ; } { name bottomWaterCellSet ; type cellSet ; action new ; source cellToCell ; set heaterCellSet ; } { name bottomWaterCellSet ; type cellSet ; action add ; source cellToCell ; set leftSolidCellSet ; } { name bottomWaterCellSet ; type cellSet ; action add ; source cellToCell ; set rightSolidCellSet ; } { name bottomWaterCellSet ; type cellSet ; action add ; source cellToCell ; set topAirCellSet ; } { name bottomWaterCellSet ; type cellSet ; action invert ; } { name bottomWater ; type cellZoneSet ; action new ; source setToCellZone ; set bottomWaterCellSet ; } ) |

