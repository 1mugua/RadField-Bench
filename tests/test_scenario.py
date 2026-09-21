from pathlib import Path

import pytest

from radfield_bench.scenario import ScenarioError, load_scenario


ROOT = Path(__file__).parents[1]


def test_reference_scenario_loads():
    scenario = load_scenario(ROOT / "scenarios/train/open_room_single_source.yaml")
    assert scenario.scenario_id == "train_open_room_single_source_v0"
    assert len(scenario.sources) == 1
    assert scenario.task.task_type == "source_localization"


def test_unknown_obstacle_material_is_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        """schema_version: '0.1'
scenario_id: bad
split: train
seed: 1
time_step_s: 0.1
world:
  bounds: {x_min: 0, x_max: 2, y_min: 0, y_max: 2}
  obstacles: [{id: wall, x_min: 1, x_max: 1.1, y_min: 0, y_max: 2, material: mystery}]
materials: {air: {linear_attenuation_per_m: 0}}
sources: [{id: s, x: 0.5, y: 0.5, reference_cps_at_1m: 10}]
detector: {integration_time_s: 1, background_cps: 0}
robot: {start: {x: 0.2, y: 0.2}, max_linear_velocity_mps: 1, max_angular_velocity_rps: 1}
task: {type: source_localization, max_steps: 10, dose_budget: 100}
""",
        encoding="utf-8",
    )
    with pytest.raises(ScenarioError, match="unknown material"):
        load_scenario(path)


def test_invalid_detector_efficiency_is_rejected(tmp_path):
    source = (ROOT / "scenarios/train/open_room_single_source.yaml").read_text(
        encoding="utf-8"
    )
    path = tmp_path / "bad-efficiency.yaml"
    path.write_text(source.replace("efficiency: 0.85", "efficiency: 1.5"), encoding="utf-8")
    with pytest.raises(ScenarioError, match="efficiency"):
        load_scenario(path)
