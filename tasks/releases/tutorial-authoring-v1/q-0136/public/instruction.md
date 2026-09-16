# Reconstruct molecular equilibration of periodic liquid water

You are given the three-dimensional exterior geometry and dense native observations of velocity at the terminal time. Build and run an OpenFOAM v2306 molecular-dynamics case that reproduces the supplied numerical state. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The domain is a cube with
-2.1084e-9 <= x, y, z <= 2.1084e-9. Each pair of opposing faces is periodic;
there are no physical walls or openings. The cube side length is 4.2168e-9 m
and its volume is 7.4980616965632e-26 m3. The exterior geometry does not
prescribe a volume mesh.

The physical family is classical molecular dynamics of electrically neutral,
rigid four-site water molecules. Relative to the oxygen site, the two hydrogen
sites are at (+/-7.56950327263661e-11, 5.85882276618295e-11, 0) m and the
massless negative-charge site is at (0, 1.5e-11, 0) m. Each hydrogen has mass
1.67353255e-27 kg and charge +8.3313177324e-20 C. Oxygen has mass
2.6560176e-26 kg and zero charge. The massless site has charge
-1.66626354648e-19 C. Thus each molecule has mass 2.99072411e-26 kg and zero
net charge.

Oxygen sites interact through a Lennard-Jones potential with sigma
3.154e-10 m, epsilon 1.07690722e-21 J and a 1.0e-9 m cutoff. Electrostatic
interactions use the stated site charges, a damped Coulomb form with damping
coefficient 2.0e9 1/m, a 1.0e-9 m cutoff and shifted-force cutoff treatment.
There is no gravity or other known external body force, and molecules are not
tethered.

Initially the nominal mass density is 980 kg/m3, the temperature is 298 K and
the bulk velocity is zero. Molecular centres occupy a face-centred-cubic
four-point basis, with basis coordinates (0,0,0), (0,1/2,1/2),
(1/2,0,1/2) and (1/2,1/2,0), and share the stated initial reference
orientation. The temperature-control target during equilibration is 298 K.
The target data describe physical time t = 5.0e-12 s.

The periodicity, zero external force, interaction family and parameters, and
temperature target are known. Spatial discretization, microscopic thermal
velocity realization, trajectory-integration details and any additional
numerical equilibration choices are not uniquely determined by the terminal
observations; infer and justify a plausible realization. A microscopic
trajectory is sensitive to these choices, so the supplied result is one
realization, not uniquely identifiable ground truth.

## Deliverable

Submit a successful native calculation with the velocity field saved at
t = 5.0e-12 s in m/s, using physical coordinates in the supplied geometry.
Retain native molecular state fields only when they are genuinely produced by
your model; do not synthesize continuum fields from particles solely to match a
target. Choose the mesh and numerical controls within the execution budget.

Give a short final modeling note separating known information, inferred
choices, unresolved alternatives and verified results. No particular solver,
dictionary layout, volume-mesh prescription or long explanation is required.

The target data may be used for analysis and calibration, including physically
interpretable material or equilibration parameters. Do not initialize from the
terminal target field or target particle state, prescribe target values in the
interior, construct pointwise forcing that pins the result to the observations,
or substitute target data for native output. Start from the stated physical
initial condition. This is a reconstruction task, not a test of copying or
restarting an existing terminal solution.
