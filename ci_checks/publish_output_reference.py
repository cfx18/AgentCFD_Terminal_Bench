"""Explicit offline publication; never starts agents or OpenFOAM."""
import argparse
import json
from agentcfd_bench.output_release import build

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.project, args.output), indent=2))
