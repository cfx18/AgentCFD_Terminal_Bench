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

At the final saved iterate, compare T and vertical velocity Uy profiles
in 20 equal x bins over [0, 0.076] m and 20 equal y bins over [0, 2.18] m, each
spanning the full perpendicular cross-section. Compare area-integrated heat
rates at the hot x=0.076 m wall and cold x=0 wall. Native wallHeatFlux is positive
into the fluid; heat-flux density must be multiplied by face area.

Also check field signs, total cavity volume, conservation of the initial ideal-gas
mass, temperature bounds, hot/cold heat directions and negligible heat at the
four adiabatic walls. Preserve T, U, absolute p, p_rgh, k, omega, nut and alphat.
Save at least two iterates when feasible for a separate stationarity diagnostic;
nearby writes alone do not prove steady convergence.
