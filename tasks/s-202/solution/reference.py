import copy,json
from pathlib import Path
from agentcfd_bench.edge_packages import controls,alternative
ROOT=Path(__file__).resolve().parents[1]
def reference_files(): return json.loads((ROOT/'solution/source'/ (ROOT.name+'.json')).read_text())['active_inputs']
def qualification_controls(): return controls(reference_files(),ROOT.name)
def alternative_numerics(): return alternative(reference_files())
def fabricate_measurements(measures):
    result=copy.deepcopy(measures)
    result['last_initial_residual']['value']+=1
    return result
