"""Private accepted-reference grader, never mounted for the agent."""
from pathlib import Path
from agentcfd_bench.accepted_reference import create
_checker = create(Path(__file__).resolve().parents[1])
safety_inputs = _checker.safety_inputs
physics_contract = _checker.physics_contract
extract = _checker.extract
reference_observations = _checker.reference_observations
validate_measurements = _checker.validate_measurements
parse_action = _checker.parse_action
evaluate = _checker.evaluate
