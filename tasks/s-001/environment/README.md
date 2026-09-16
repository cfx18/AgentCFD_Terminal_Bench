# Agent environment

The existing Codex/bubblewrap adapter supplies an anonymous empty `/work`.
Only the public instruction, budget, own files and read-only native artifacts
are exposed. No task root, solution, tests, host credentials or solver is mounted.
The runtime is the pinned cluster/Apptainer adapter, not an untested Docker image.
