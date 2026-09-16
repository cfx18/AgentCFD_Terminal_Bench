"""Private task-owned binding to the shared independent verifier."""
import json
from pathlib import Path
from agentcfd_bench.tutorial_acceptance import TutorialAcceptance

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/name).read_text())
_acceptance = TutorialAcceptance(read('solution/profile.json'), read('solution/baseline.json'),
                                 read('environment/acceptance-policy.json'))
safety_inputs = _acceptance.safety_inputs
physics_contract = _acceptance.physics_contract
parse_action = _acceptance.parse_action
extract = _acceptance.extract
evaluate = _acceptance.evaluate
