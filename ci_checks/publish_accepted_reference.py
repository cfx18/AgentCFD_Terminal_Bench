"""Freeze an explicitly accepted reference release; no model or native calls."""
import argparse
import json
from pathlib import Path

from agentcfd_bench.accepted_release import build


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--output', required=True, help='New private release directory; never overwritten')
    args = parser.parse_args()
    print(json.dumps(build(args.project, args.output), indent=2))
