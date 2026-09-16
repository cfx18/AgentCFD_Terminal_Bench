Units: metres. domain.stl describes the exterior geometry.
Its triangles are a surface representation, NOT a computational mesh or mesh-size requirement.
Choose your own mesh and discretization. Boundary names label geometry only;
physical boundary conditions and dimensional assumptions are defined by the task statement.
bottomWater.stl, topAir.stl, heater.stl, leftSolid.stl, rightSolid.stl are material-region boundaries.
Each is a closed surface. A to_REGION label denotes a shared material interface.
Keep the same physical domains; choose independent volume meshes, without gaps or overlaps.
domain.stl is only the outer envelope, not an additional material region.
