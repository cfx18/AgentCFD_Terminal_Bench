# Reconstruct an ignited methane-air flame in a pipe lattice

You are given the three-dimensional exterior geometry and dense synthetic observations of a short-duration reactive-flow state. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original numerical configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code, and web resources.

## Known physical information

Coordinates are in metres. The gas domain is the rectangular enclosure

`-19.4 <= x <= 23.66`, `-19.42 <= y <= 23.68`, `0 <= z <= 23.17`.

The floor at `z = 0` is a stationary impermeable wall. The other five exterior faces are open to an ambient pressure of 100000 Pa; there is no imposed mean inflow. The exterior STL contains only these surfaces and does not prescribe a volume mesh.

A stationary lattice of circular pipes occupies the corner region near the floor. Every pipe has diameter 0.082 m. Define `q_s = 0.13325 + 0.2665 s` for any integer `s = 0,...,15` and `r_m = 0.13325 + 0.2665 m` for `m = 0,...,7`:

- 256 vertical pipes have axes at every pair `(x,y) = (q_n,q_l)` and length 2.132 m in the z direction from the floor;
- 128 x-directed pipes span `0 <= x <= 4.26`, at every `(y,z) = (q_n,r_m)`;
- 128 y-directed pipes span `0 <= y <= 4.26`, at every `(x,z) = (q_n,r_m)`.

The target belongs to the compressible, premixed methane-air deflagration family with obstacle-induced drag and turbulence. The gases obey a perfect-gas equation of state with temperature-dependent heat capacity and Sutherland transport. The methane, oxidant, and burnt-product molar masses used in the target realization are 16.043, 28.8504, and 27.633 kg/kmol, respectively; the stoichiometric air-to-fuel mass ratio is 17.1667. Gravity is zero. There is no radiation, phase change, moving boundary, or externally imposed bulk flow. Pipe heat transfer was not resolved in the target realization, so treating the solid obstruction as adiabatic is consistent with the supplied data.

Initially the gas is at rest at 287 K and 100000 Pa. The box `0 <= x <= 4`, `0 <= y <= 4`, `0 <= z <= 2` contains a stoichiometric methane-air mixture with fuel mixture fraction 0.0550457705582192; the remainder of the domain is oxidant with zero fuel mixture fraction. The gas is initially entirely unburnt. The initial turbulence levels are `k = 1.5e-4 m2/s2` and `epsilon = 1e-5 m2/s3`.

Ignition is localized around `(2.129836154, 2.129836154, 0.1773225)` in a region of diameter 0.0525394295667244 m, beginning at `t = 2e-5 s`. The exact numerical source profile, flame-wrinkling closure, obstacle-drag homogenization, and turbulence closure are not uniquely determined by the observations; infer and justify a plausible realization. The pipe lattice may be resolved or represented as a physically consistent sub-grid obstruction. The supplied target is one finite numerical realization, not uniquely identifiable ground truth.

## Deliverable

Submit a successful native calculation with velocity, absolute pressure, absolute temperature, density, unburnt fraction and fuel mixture fraction saved at `t = 0.124524 s`. Their units are m/s, Pa, K, kg/m3, dimensionless and dimensionless. If your selected physical model evolves flame wrinkling, turbulence, laminar or turbulent flame speed, or unburnt temperature, retain those native fields as well. The configured target stop was 0.125 s, but 0.124524 s is the actual supplied observation time; do not silently reinterpret the data as a steady state.

Give a short final modeling note separating known information, inferred choices, unresolved alternatives and verified results. No particular solver, dictionary recipe, mesh topology, closure implementation, or long explanation is required. Reconstruction accuracy does not establish that the inferred closure or ignition model is uniquely correct.

The target data may be used for analysis and calibration of physically interpretable parameters. Do not initialize from any target terminal field, prescribe target values inside the domain, construct pointwise forcing that pins the solution to the observations, or substitute supplied data for native output. Start from the stated physical initial condition. This is a reconstruction task, not a copying or restart task.
