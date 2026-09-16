#!/usr/bin/env bash
# Invoke with bash; no executable-bit or environment installation is required.
set -euo pipefail
science_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
science_project_dir="$(cd -- "$science_script_dir/.." && pwd)"
export PYTHONPATH="$science_project_dir:$science_script_dir${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
exec /usr/bin/python3 -B "$science_script_dir/submit_science.py" "$@"
