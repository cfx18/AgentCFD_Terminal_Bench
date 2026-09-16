# Reconstruct steady heat diffusion in a thin rectangular plate

You are given the three-dimensional exterior geometry and dense numerical observations of temperature. Build and run an OpenFOAM v2306 case that reproduces the observed scalar field. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The body is a rectangular plate occupying 0 <= x <= 0.20, 0 <= y <= 0.12 and 0 <= z <= 0.01. It is modeled as two-dimensional through its thickness; the two z-normal faces do not carry through-thickness heat flux. The medium is homogeneous and isotropic, with no known internal material discontinuity or volumetric heat source.

The problem family is linear steady heat diffusion. The scalar is dimensioned as temperature and the observations are in kelvin. The archived realization assigns a common coefficient of 4e-5, but does not declare its dimensions and supplies neither density nor heat capacity. Consequently, a particular physical material and transient diffusivity cannot be identified from the available information; for a homogeneous steady Laplace problem the common coefficient magnitude does not determine the temperature field.

The numerical initial field is uniform 0 K. Values on this scale, including 0 K, make this a synthetic mathematical temperature example rather than a physically credible absolute-temperature experiment. All forcing is boundary forcing: there is no volumetric source. The locations and values of prescribed-temperature and insulated portions of the in-plane boundary are not supplied to the reconstructor; infer and justify a plausible realization from the geometry and observations. Do not claim that boundary forcing or interface treatment is uniquely identifiable.

The observation endpoint is the state labeled 50 in a steady-state iteration. It is not 50 seconds and has no defensible physical timestamp. The original numerical realization used loosely exchanged interface values, so its finite endpoint may retain coupling-iteration error and need not be a certified continuum steady state.

## Deliverable

Submit a successful native calculation with temperature saved at the observation endpoint. Use the supplied physical coordinates, choose your own mesh and numerical controls, and report temperature in kelvin. The target is a finite numerical reconstruction; the exterior geometry does not prescribe a volume mesh, subdomain partition or solver dictionary.

Give a short final modeling note separating known information, inferred boundary choices, unresolved physical/numerical alternatives and verified results. No particular reasoning sequence, solver name, configuration template or long explanation is required. The original configuration is only one realization and is not uniquely identifiable ground truth.

Target data may be used for analysis and calibration of physically interpretable boundary parameters. Do not initialize or prescribe the internal field from target values, construct pointwise forcing that pins the interior to the target, or substitute target data for native output. Start from the stated uniform initial condition. This is a reconstruction task, not a copying or restart task.
