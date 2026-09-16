Build all OpenFOAM v2306 inputs from scratch in /work. No starter case is supplied.
Problem: incompressible Newtonian transient planar Couette flow. SI units.
Domain x=[0,1], y=[0,1], z=[0,0.1] m. Uniform single-hex Cartesian mesh,
4 x 20 x 1 cells, canonical vertices (0,0,0),(1,0,0),(1,1,0),(0,1,0),
(0,0,0.1),(1,0,0.1),(1,1,0.1),(0,1,0.1), block (0 1 2 3 4 5 6 7).
Use patch names left/right (cyclic pair in x), bottom/top (wall), frontAndBack (empty).
Initially U=(0,0,0) and kinematic p=0 everywhere. At t=0 the top wall starts at
U=(1,0,0) m/s; bottom stays U=(0,0,0). On both walls p has zeroGradient.
On left/right both U and p are cyclic; frontAndBack is empty for both fields.
Kinematic viscosity nu=0.1 m^2/s. No body force, no pressure gradient, laminar.
Use icoFoam; solve from startTime=0 to endTime=2 s, stopAt=endTime, deltaT<=0.01 s,
fixed time step. Use ASCII, uncompressed output with sufficient precision;
retain and write the t=2 fields. Choose your own stable schemes/linear solvers.
Include a pressure reference. Generate mesh with blockMesh; the service also runs checkMesh.
This pilot accepts self-contained literal ASCII dictionaries only: no includes,
macros, dynamic code, custom libraries, function objects or supplied polyMesh.
Do not supply 0/phi: face flux must be initialized by the solver from U.
Equivalent disabled-switch spellings (off/no/false/0) and omitted empty edges/
mergePatchPairs lists are accepted. Omitted mesh scale means one metre per unit.
Additional passive ASCII input dictionaries are not rejected merely by filename;
all submitted files still undergo the same safety checks. Mesh transforms and
noncanonical cell layouts are outside this pilot's supported representation.
No shell scripts are executed in the solver service. You may write your own
Python/shell postprocessor in /work, outside 0/, constant/, system/.

To submit a real run: write system/science-action.json containing exactly
{"action":"run","solver":"icoFoam"}, then finish this Codex turn. The external
service snapshots inputs, runs OpenFOAM, and resumes THIS session with native logs.
Only official run submissions count. There is no fixed failed-submission limit.
Never claim native execution based on your local shell: the solver is not mounted here.
After a completed run, immutable raw fields and sanitized logs are mounted read-only
under /artifacts/<run_id>/. Inspect and postprocess those actual files yourself.
To submit quantitative results, replace the action file with:
{"action":"report","run_id":"<run_id>","measurements":{
 "ux_profile":{"unit":"m/s","value":[20 numbers]},
 "uy_rms":{"unit":"m/s","value":0.0},
 "final_time":{"unit":"s","value":2.0},
 "ux_final_initial_residual":{"unit":"1","value":0.0}}}
ux_profile: mean Ux across the 4 x-cells at each y-cell centre, ordered bottom to top,
from the final t=2 internal field. uy_rms: RMS Uy over all 80 cells at t=2.
final_time: actual final field time. ux_final_initial_residual: the last logged
Initial residual for Ux (diagnostic only, NOT a physical correctness criterion).
The verifier independently extracts all four measurements from frozen output.
Report tolerance: 1e-6 absolute + 1e-5 relative against extracted values.
Physical checks: max error of the velocity profile against the transient analytic
solution <=0.005 m/s, Uy RMS<=1e-6 m/s, time=2 within 1e-8 s; the declared
geometry, physics, boundaries and initial condition must also be preserved.
Incorrect reports may be corrected, or you may submit a new run, within the same
total budget. Native errors/format feedback are available, hidden reference values are not.
Do not seek references, evaluator source, prior results, or external documentation.
