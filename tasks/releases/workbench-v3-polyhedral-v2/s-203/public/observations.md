# Independently extracted observations

Keep your actual native mesh and solution fields. The evaluator reads the frozen
solver output, independently exports cell geometry, and compares physical
observations with a hidden, expert-accepted finite numerical reference. No
self-reported JSON is required. A successful OpenFOAM exit alone is not a pass.

You choose cell types, grading, resolution, cell ordering, region names and patch
names. Observation regions and wall names below identify physical locations, not
required OpenFOAM identifiers. Statistics use volume or face-area weights. Cells
crossing an observation boundary contribute by their actual geometric overlap;
each stored cell value is treated as piecewise constant within that polyhedron.
Binary native output is supported. Preserve the field names and physical units
of the quantities being observed; the evaluator generates C/V itself.

Residuals, saved-iterate changes and heat balance are recorded where available.
Missing diagnostic evidence is not zero. Agreement with this finite reference
does not certify mesh independence or strict steady-state convergence. Report
remaining numerical uncertainty honestly.

At physical time 1.5 s, compare volume-averaged T, U, kinematic p, k,
epsilon and nut in fixed physical subvolumes. Split the inlet passage
0 < x < 0.2 m into five equal axial segments. Split each branch of the vertical
passage (x from 0.2 to 0.22 m), y from -0.21 to -0.01 m and from 0.01 to 0.21 m,
into five equal y segments; keep the central junction (-0.01 < y < 0.01 m) as
one subvolume. Every subvolume spans the full thickness 0 < z < 0.02 m.
Temperature differences use a 300 K reference offset. The separately reported
temperature excess above the 315 K inlet is important for diagnosing heating.
