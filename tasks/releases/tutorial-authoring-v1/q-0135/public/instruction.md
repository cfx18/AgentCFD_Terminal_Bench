# Reconstruct isothermal molecular equilibration in a periodic argon cube

You are given the three-dimensional exterior geometry and dense synthetic observations of the reported velocity quantity. Build and run an OpenFOAM v2306 case that reproduces these observations. Generate your own volume mesh and case inputs. The original configuration is not supplied. You may inspect all supplied observations and consult general OpenFOAM documentation, source code and web resources.

## Known physical information

Coordinates are in metres. The domain is a cube centred at the origin, with -2.462491658e-9 <= x, y, z <= 2.462491658e-9. Every pair of opposite faces is periodic; there are no physical walls, openings or free surfaces.

The problem family is classical molecular-dynamics equilibration of monatomic argon. Each molecule is one neutral site with mass 6.63352033e-26 kg. The initial mass density is 1220 kg/m3, the initial temperature is 300 K, and the initial bulk velocity is zero. Molecules initially occupy an untethered simple-cubic lattice aligned with the coordinate axes and anchored at the origin. The corresponding domain mass is approximately 1.457384417e-22 kg, or 2197 argon molecules; the exact microscopic velocity realization is not supplied.

Argon sites interact through a Maitland-Smith pair potential with m = 13.0, gamma = 7.5, equilibrium-distance parameter 0.3756 nm and energy parameter 1.990108438e-21 J. The pair cutoff is 1.0 nm, with the interaction smoothly reduced near the cutoff. Electrostatic site forces vanish because the sites are uncharged. There is no gravity or other external body force, and no tethering. The system is equilibrated toward a known 300 K target. The detailed temperature-control realization and any indistinguishable microscopic history should be inferred and justified from the observations rather than claimed as uniquely identified.

The observations describe physical time t = 5.0e-11 s (50 ps). They represent one finite numerical and microscopic realization, not a mesh-independent continuum truth and not a uniquely identifiable initial random draw or thermostat mechanism.

## Deliverable

Submit a successful native molecular-dynamics calculation with the observed native velocity quantity saved at t = 5.0e-11 s in m/s, together with the native molecular state needed to interpret it. Use physical coordinates matching the supplied geometry and choose your own volume mesh and stable numerical controls. Do not add pressure or temperature fields merely to imitate a continuum-flow task; only quantities actually advanced or reported by your chosen physical model belong in the result.

Give a short final modeling note separating known information, inferred choices, unresolved microscopic alternatives and verified results. No particular reasoning sequence, solver name, dictionary recipe or long explanation is required.

The target data may be used for analysis and calibration, including physically interpretable initialization and interaction choices. Do not initialize or prescribe the target terminal velocity field, construct pointwise forces that pin the interior or individual molecules to target values, or substitute target data for native output. Start from the stated thermodynamic and bulk initial condition. This is a reconstruction task, not a copying or restart task.
