import json
from pathlib import Path

from radfield_bench.runner import run_baseline


ROOT = Path(__file__).parents[1]


def test_lawnmower_run_writes_evaluation_artifacts(tmp_path):
    metrics = run_baseline(
        ROOT / "scenarios/train/open_room_single_source.yaml",
        "lawnmower",
        tmp_path / "run",
    )
    assert "mission" in metrics
    assert (tmp_path / "run/manifest.json").exists()
    assert (tmp_path / "run/trajectory.csv").exists()
    loaded = json.loads((tmp_path / "run/metrics.json").read_text(encoding="utf-8"))
    assert loaded["scenario_id"] == "train_open_room_single_source_v0"


def test_bayesian_grid_baseline_runs(tmp_path):
    metrics = run_baseline(
        ROOT / "scenarios/train/open_room_single_source.yaml",
        "bayes-grid",
        tmp_path / "bayes-run",
    )
    assert metrics["localization"]["reported_source_count"] == 1
    assert metrics["success"] is False
    assert metrics["exposure"]["within_budget"] is False
