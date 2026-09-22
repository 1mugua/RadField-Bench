"""Deterministic scenario generator for the domain-based scenario library.

Each scenario is produced from a FamilySpec at a difficulty level with a
fixed seed. The same seed always yields the same YAML file. Scenario layout
(geometry, source placement) and the runtime random sequence share one seed,
so a scenario file is fully reproducible.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from ..models import Bounds2D, Obstacle, Scenario
from .domains import DIFFICULTIES, FAMILIES, FAMILY_INDEX, FamilySpec


def generate_scenario(
    family_key: str, difficulty: str, seed: int, instance: int
) -> Scenario:
    """Generate one scenario from a family key (``domain/family``)."""
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {DIFFICULTIES}, got {difficulty!r}")
    spec = FAMILY_INDEX[family_key]
    rng = np.random.default_rng(seed)
    bounds, obstacles = spec.world(rng, difficulty)
    sources = spec.sources(rng, difficulty, obstacles)
    detector = spec.detector(difficulty)
    robot = spec.robot(difficulty)
    task = spec.task(difficulty)

    return Scenario(
        schema_version="0.1",
        scenario_id=f"{spec.family}_{difficulty}_{instance:03d}",
        split="reference",
        seed=seed,
        time_step_s=0.25,
        world=bounds,
        materials={material.name: material for material in spec.materials},
        obstacles=obstacles,
        sources=sources,
        detector=detector,
        robot=robot,
        task=task,
        metadata={
            "domain": spec.domain,
            "family": spec.family,
            "difficulty": difficulty,
            "instance": instance,
            "description": spec.description,
            "authoring_status": "generated",
        },
    )


def scenario_to_dict(scenario: Scenario) -> dict:
    """Serialize a Scenario into the YAML mapping consumed by load_scenario."""
    world = scenario.world
    obstacles = [
        {
            "id": obstacle.obstacle_id,
            "x_min": obstacle.x_min,
            "x_max": obstacle.x_max,
            "y_min": obstacle.y_min,
            "y_max": obstacle.y_max,
            "material": obstacle.material,
        }
        for obstacle in scenario.obstacles
    ]
    materials = {
        name: {"linear_attenuation_per_m": material.linear_attenuation_per_m}
        for name, material in scenario.materials.items()
    }
    sources = [
        {
            "id": source.source_id,
            "x": source.x,
            "y": source.y,
            "reference_cps_at_1m": source.reference_cps_at_1m,
            "isotope": source.isotope,
        }
        for source in scenario.sources
    ]
    detector = {
        "integration_time_s": scenario.detector.integration_time_s,
        "background_cps": scenario.detector.background_cps,
        "efficiency": scenario.detector.efficiency,
        "max_cps": scenario.detector.max_cps,
        "dead_time_s": scenario.detector.dead_time_s,
        "min_distance_m": scenario.detector.min_distance_m,
        "directional_exponent": scenario.detector.directional_exponent,
    }
    robot = {
        "start": {
            "x": scenario.robot.start.x,
            "y": scenario.robot.start.y,
            "yaw": scenario.robot.start.yaw,
        },
        "max_linear_velocity_mps": scenario.robot.max_linear_velocity_mps,
        "max_angular_velocity_rps": scenario.robot.max_angular_velocity_rps,
        "pose_mode": scenario.robot.pose_mode,
        "odometry_noise": {
            "translation_std_m": scenario.robot.translation_noise_std_m,
            "rotation_std_rad": scenario.robot.rotation_noise_std_rad,
        },
    }
    task = {
        "type": scenario.task.task_type,
        "max_steps": scenario.task.max_steps,
        "dose_budget": scenario.task.dose_budget,
    }
    if scenario.task.goal is not None:
        task["goal"] = {"x": scenario.task.goal[0], "y": scenario.task.goal[1]}
        task["goal_tolerance_m"] = scenario.task.goal_tolerance_m
    task["localization_tolerance_m"] = scenario.task.localization_tolerance_m

    return {
        "schema_version": scenario.schema_version,
        "scenario_id": scenario.scenario_id,
        "split": scenario.split,
        "seed": scenario.seed,
        "time_step_s": scenario.time_step_s,
        "metadata": dict(scenario.metadata),
        "world": {"bounds": {
            "x_min": world.x_min,
            "x_max": world.x_max,
            "y_min": world.y_min,
            "y_max": world.y_max,
        }, "obstacles": obstacles},
        "materials": materials,
        "sources": sources,
        "detector": detector,
        "robot": robot,
        "task": task,
    }


def write_scenario(scenario: Scenario, output_dir: str | Path) -> Path:
    domain = scenario.metadata["domain"]
    path = Path(output_dir) / domain / f"{scenario.scenario_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(scenario_to_dict(scenario), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def generate_all(
    output_dir: str | Path,
    instances_per_difficulty: int = 2,
    seed_base: int = 10_000,
) -> list[Path]:
    """Generate the full first batch of the domain scenario library.

    All families x all difficulties x N instances, deterministic under a
    fixed seed_base.
    """
    written: list[Path] = []
    counter: dict[tuple[str, str], int] = {}
    for spec in FAMILIES:
        for difficulty in DIFFICULTIES:
            for _ in range(instances_per_difficulty):
                key = (spec.family, difficulty)
                counter[key] = counter.get(key, 0) + 1
                instance = counter[key]
                seed = seed_base + len(written) * 3 + instance
                scenario = generate_scenario(
                    f"{spec.domain}/{spec.family}", difficulty, seed, instance
                )
                written.append(write_scenario(scenario, output_dir))
    return written


def family_summary() -> list[dict[str, object]]:
    """Human-readable inventory of the domain library."""
    rows: list[dict[str, object]] = []
    for spec in FAMILIES:
        rows.append(
            {
                "domain": spec.domain,
                "family": spec.family,
                "description": spec.description,
                "difficulties": list(DIFFICULTIES),
            }
        )
    return rows


__all__ = [
    "FamilySpec",
    "generate_scenario",
    "scenario_to_dict",
    "write_scenario",
    "generate_all",
    "family_summary",
]
