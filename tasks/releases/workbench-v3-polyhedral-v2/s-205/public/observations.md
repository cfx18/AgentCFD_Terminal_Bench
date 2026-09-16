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

At physical time 0.007 s, compare rho, p, T and axial velocity Ux in
40 equal x bins over [-5, 5] m, each spanning the full 2 m by 2 m cross-section.
Transverse mesh subdivision is allowed. Preserve rho, p, T and U. Also evaluate
total volume, mass, axial momentum, total energy, transverse velocity and the
ideal-gas equation of state. These checks use actual native values, not the
analytic solution substituted for the computed fields.
