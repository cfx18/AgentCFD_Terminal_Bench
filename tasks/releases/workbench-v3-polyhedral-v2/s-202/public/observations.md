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

At physical time 100 s, compare T in each of the five supplied material
volumes, and U, absolute/gauge p as specified in the question, and p_rgh in the
two fluids. Split each material into intersections with four equal x slices over
[-0.1, 0.1] m and two equal z slices over [-0.05, 0.05] m. Only nonempty physical
intersections are compared. Compute volume means in those subvolumes. Temperature
error is scaled by the reference temperature rise above 300 K, not absolute
temperature. Preserve previous writes and native fluxes for expert diagnostics.
