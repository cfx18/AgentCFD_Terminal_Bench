# Reconstruct buoyant flow coupled to a thermally conducting ceiling

You are given the three-dimensional exterior geometry and dense synthetic observations of gas velocity, temperature, absolute pressure, and ceiling-surface temperature. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume and surface meshes and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The sealed rectangular room occupies 0 <= x <= 10, 0 <= y <= 5, and 0 <= z <= 10. All six gas boundaries are stationary, impermeable, and no-slip. The surface at y = 0 is the floor and the surface at y = 5 is a thin conducting ceiling; the other four surfaces are ordinary side walls.

The problem family is transient buoyancy-driven compressible air flow with heat transfer, turbulence, participating grey radiation, and conjugate heat transfer to the ceiling shell. Gravity is (0, -9.81, 0) m/s2. The gas is calorically perfect with molar mass 28.9 kg/kmol, constant specific heat 1000 J/(kg K), dynamic viscosity 1.8e-5 Pa s, and molecular Prandtl number 0.7. Its grey absorption and emission coefficients are 0.01 m-1, with no scattering or soot. The wall surfaces have emissivity and absorptivity 0.7 and zero transmissivity.

The known thermal forcing is as follows. The floor is held at 700 K. The four side walls are adiabatic. The ceiling is a 1 mm shell with density 1000 kg/m3, specific heat 600 J/(kg K), and thermal conductivity 200 W/(m K). Between the gas and shell is a 1 mm contact layer of conductivity 0.02 W/(m K). The outer side of the shell loses heat by convection to an environment at 290 K with heat-transfer coefficient 10 W/(m2 K), and the shell perimeter is held at 300 K. There are no openings, moving walls, volumetric heat sources, phase change, or mass exchange.

Initially the gas is at rest at 300 K and absolute pressure 100000 Pa; these values and the sealed 500 m3 volume define its initial mass. The ceiling shell is initially at 300 K. Turbulence closure, radiation discretization, mesh resolution, numerical controls, and any closure-specific initial variables are not prescribed. Infer and justify plausible choices from the observations. Different choices may be observationally similar, so do not claim that these details are uniquely identifiable.

The supplied observations describe physical time t = 400 s. They are one finite numerical realization, not a uniquely identifiable ground-truth configuration or a certification of continuum or steady-state convergence.

## Deliverable

Submit a successful native calculation with gas velocity, gas temperature, absolute thermodynamic pressure, and ceiling-shell temperature saved at t = 400 s. Pressure is in Pa and includes the hydrostatic contribution. Choose your own meshes, closure realization, and numerical controls within the execution budget; preserve the physical geometry, materials, initial state, and forcing stated above.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives, and verified results. No particular reasoning sequence, solver name, dictionary recipe, or configuration template is required. Concise decision summaries during work are welcome; reconstruction accuracy does not by itself prove that an inferred closure is physically unique.

The target data may be used for analysis and calibration, including physically interpretable closure parameters. Do not initialize or prescribe the solution from the target internal fields, construct pointwise forcing that pins the interior or shell to the target, or substitute supplied target data for native output. Start from the stated uniform physical initial condition. This is a reconstruction task, not a copying or restart task.
