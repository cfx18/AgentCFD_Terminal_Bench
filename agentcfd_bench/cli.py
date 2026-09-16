"""Thin public entry points. New runs are explicit; status/report are read-only."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser(prog="agentcfd-bench")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        p = commands.add_parser(name)
        p.add_argument("experiment")
        if name == "run":
            p.add_argument("--allow-paid", action="store_true")
    for name in ("resume", "status", "report"):
        p = commands.add_parser(name)
        p.add_argument("run_id")
        if name == "resume":
            p.add_argument("--allow-paid", action="store_true")
    p = commands.add_parser("regrade", help="Regrade a submitted answer without model calls")
    p.add_argument("run_id")
    p.add_argument("task_id")
    args = parser.parse_args()
    if args.command == "prepare":
        from .tasks.experiment import prepare

        value = prepare(args.experiment)
    elif args.command in ("status", "report"):
        from .reports.summary import report, markdown

        value = (
            report(args.run_id) if args.command == "status" else markdown(args.run_id)
        )
    elif args.command == "regrade":
        from .grading.regrade import regrade

        value = regrade(args.run_id, args.task_id)
    elif args.command == "run":
        if not args.allow_paid:
            parser.error("run requires explicit --allow-paid; prepare is free")
        from .controller import run

        value = run(args.experiment)
    else:
        if not args.allow_paid:
            parser.error("resume requires explicit --allow-paid")
        from pathlib import Path
        from .controller import resume, frozen_resume

        frozen = Path(args.run_id).resolve() / "code/agentcfd_bench"
        value = (
            resume(args.run_id)
            if Path(__file__).resolve().parent == frozen
            else frozen_resume(args.run_id)
        )
    print(
        value
        if isinstance(value, str)
        else json.dumps(value, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
