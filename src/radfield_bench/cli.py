from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import run_baseline
from .scenario import load_scenario


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="radfield")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a scenario file")
    validate.add_argument("scenario")

    run = subparsers.add_parser("run", help="Run a reference baseline")
    run.add_argument("scenario")
    run.add_argument(
        "--baseline",
        choices=("random", "lawnmower", "bayes-grid"),
        default="lawnmower",
    )
    run.add_argument("--output", required=True)
    run.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override the scenario seed for environment and agent RNGs",
    )

    evaluate = subparsers.add_parser("evaluate", help="Print metrics from a completed run")
    evaluate.add_argument("run_directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        scenario = load_scenario(args.scenario)
        print(
            json.dumps(
                {
                    "valid": True,
                    "scenario_id": scenario.scenario_id,
                    "split": scenario.split,
                    "source_count": len(scenario.sources),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "run":
        metrics = run_baseline(
            args.scenario, args.baseline, args.output, seed=args.seed
        )
        print(json.dumps(metrics, indent=2))
        return 0
    metrics_path = Path(args.run_directory) / "metrics.json"
    if not metrics_path.exists():
        raise SystemExit(f"No metrics.json found in {args.run_directory}")
    print(metrics_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
