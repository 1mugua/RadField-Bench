from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .baselines import make_baseline
from .environment import RadFieldEnv
from .evaluation import evaluate_episode
from .scenario import load_scenario


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def run_baseline(
    scenario_path: str | Path,
    baseline_name: str,
    output_dir: str | Path,
    seed: int | None = None,
) -> dict[str, object]:
    scenario_path = Path(scenario_path).resolve()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    scenario = load_scenario(scenario_path)
    actual_seed = scenario.seed if seed is None else seed
    env = RadFieldEnv(scenario)
    agent = make_baseline(baseline_name)
    agent.reset(scenario, seed=actual_seed)
    observation = env.reset(seed=actual_seed)

    while not env.state.terminated and not env.state.truncated:
        observation, _, _, _, _ = env.step(agent.act(observation))

    estimate = agent.estimate()
    metrics = evaluate_episode(scenario, env.state, env.history, estimate)
    manifest = {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario_id": scenario.scenario_id,
        "scenario_path": str(scenario_path),
        "scenario_sha256": _sha256(scenario_path),
        "scenario_seed": scenario.seed,
        "run_seed": actual_seed,
        "baseline": baseline_name,
        "benchmark_version": "0.1.0.dev0",
    }

    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (output / "estimate.json").write_text(
        json.dumps(estimate, indent=2), encoding="utf-8"
    )
    (output / "metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    _write_trajectory(output / "trajectory.csv", env.history)
    return metrics


def _write_trajectory(path: Path, history: list[dict[str, object]]) -> None:
    fieldnames = [
        "step",
        "time_s",
        "x",
        "y",
        "yaw",
        "counts",
        "count_rate_cps",
        "cumulative_exposure",
        "remaining_exposure_budget",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in history:
            pose = row["pose"]
            writer.writerow(
                {
                    "step": row["step"],
                    "time_s": row["time_s"],
                    "x": pose["x"],
                    "y": pose["y"],
                    "yaw": pose["yaw"],
                    "counts": row["counts"],
                    "count_rate_cps": row["count_rate_cps"],
                    "cumulative_exposure": row["cumulative_exposure"],
                    "remaining_exposure_budget": row["remaining_exposure_budget"],
                }
            )

