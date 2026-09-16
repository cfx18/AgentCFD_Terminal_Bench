# Observation and output contract

Read `observations/schema.json` and `observations/fields.csv`. All target samples are public synthetic internal-cell values. Each row gives a genuine native mesh cell centroid, its positive geometric cell volume, and the actual saved volumetric fields. The coordinates are observation locations, not a requirement to reuse the reference mesh. `geometry/domain.stl` contains only the exterior boundary; its surface triangulation and labels do not prescribe a volume mesh or numerical boundary names.

The primary reconstruction fields are velocity `U`, absolute pressure `p`, absolute temperature `T`, density `rho`, unburnt fraction `b`, and fuel mixture fraction `ft`. Additional closure fields are supplied for diagnosis but need not dictate the solver family. Field dimensions, units, component counts, timestamps and mesh provenance are recorded in the schema. The static open-volume fraction `betav` is sampled from the refined starting mesh and is not a terminal thermodynamic field.

An evaluator should use containing-cell sampling at every observation coordinate and the supplied positive volumes for quadrature. Report missing coverage and nonfinite values explicitly. For vectors, compare vector magnitude errors rather than scoring components independently. Absolute pressure is physically anchored to the 100000 Pa ambient level; do not silently remove a constant pressure offset, though a separately reported mean-aligned pressure-shape diagnostic is useful.

This target is finite and numerically imperfect. In particular, its unburnt fraction undershoots zero near the ignition region, and the state is still transient. Reconstruction metrics measure agreement with this numerical realization; they do not certify continuum convergence or physical validity.

Public observations may be used for calibration, but they may not be copied into initialized or prescribed interior fields and may not be enforced by pointwise source terms. The authoritative output remains a native calculation evolved from the stated initial condition.
