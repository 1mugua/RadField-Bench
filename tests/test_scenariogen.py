"""Tests for the domain-based scenario generator."""
from pathlib import Path

import pytest

from radfield_bench.scenariogen import (
    DIFFICULTIES,
    FAMILIES,
    generate_all,
    generate_scenario,
    scenario_to_dict,
)
from radfield_bench.scenario import load_scenario


def test_generate_is_deterministic_for_same_seed():
    a = scenario_to_dict(generate_scenario("source_search/open_area", "simple", seed=42, instance=1))
    b = scenario_to_dict(generate_scenario("source_search/open_area", "simple", seed=42, instance=1))
    assert a == b


def test_different_seeds_give_different_layouts():
    a = generate_scenario("source_search/open_area", "medium", seed=1, instance=1)
    b = generate_scenario("source_search/open_area", "medium", seed=2, instance=1)
    assert (a.sources[0].x, a.sources[0].y) != (b.sources[0].x, b.sources[0].y)


def test_all_families_cover_all_difficulties():
    for spec in FAMILIES:
        for difficulty in DIFFICULTIES:
            scenario = generate_scenario(
                f"{spec.domain}/{spec.family}", difficulty, seed=7, instance=1
            )
            assert scenario.metadata["domain"] == spec.domain
            assert scenario.metadata["family"] == spec.family
            assert scenario.metadata["difficulty"] == difficulty
            assert scenario.task.task_type in ("source_localization", "safe_exploration")


def test_generated_all_writes_loadable_scenarios(tmp_path):
    paths = generate_all(tmp_path, instances_per_difficulty=2, seed_base=10_000)
    assert len(paths) == len(FAMILIES) * len(DIFFICULTIES) * 2
    for path in paths:
        scenario = load_scenario(path)
        assert scenario.metadata["authoring_status"] == "generated"
        assert scenario.robot.pose_mode == "noisy_odometry"


def test_sources_inside_world_and_outside_obstacles():
    for spec in FAMILIES:
        for difficulty in DIFFICULTIES:
            scenario = generate_scenario(
                f"{spec.domain}/{spec.family}", difficulty, seed=5, instance=1
            )
            for source in scenario.sources:
                assert scenario.world.contains(source.x, source.y)
                for obstacle in scenario.obstacles:
                    assert not obstacle.contains(source.x, source.y)


def test_scenario_roundtrip_preserves_core_fields(tmp_path):
    scenario = generate_scenario("waste_management/waste_store", "hard", seed=11, instance=1)
    path = tmp_path / "roundtrip.yaml"
    path.write_text(
        __import__("yaml").safe_dump(scenario_to_dict(scenario), sort_keys=False),
        encoding="utf-8",
    )
    loaded = load_scenario(path)
    assert loaded.scenario_id == scenario.scenario_id
    assert loaded.task.dose_budget == scenario.task.dose_budget
    assert loaded.detector.background_cps == scenario.detector.background_cps
    assert len(loaded.sources) == len(scenario.sources)
