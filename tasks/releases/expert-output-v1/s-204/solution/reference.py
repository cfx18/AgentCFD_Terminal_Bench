"""Private input evidence; no reference run is scheduled."""
import json
from pathlib import Path
def reference_files():
    return json.loads((Path(__file__).parent/'physics-inputs.json').read_text())
