"""Private original bytes and explicit author-only controls; never agent mounted."""
import copy
import json
from pathlib import Path
from agentcfd_bench.tutorial_packages import controls, alternative_numerics as alternative

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/name).read_text())
def reference_files():
    return {k:v['text'] for k,v in read('solution/original.json')['original_inputs'].items()}
def qualification_controls():
    return controls(reference_files(),read('solution/profile.json'))
def alternative_numerics():
    return alternative(reference_files(),read('solution/profile.json'))
def fabricate_measurements(measurements):
    value = copy.deepcopy(measurements)
    value['speed_cell_max']['value'] += 1
    return value
