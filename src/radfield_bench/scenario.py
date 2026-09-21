from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    Bounds2D,
    DetectorConfig,
    Material,
    Obstacle,
    Pose2D,
    RadiationSource,
    RobotConfig,
    Scenario,
    TaskConfig,
)


class ScenarioError(ValueError):
    """Raised when a benchmark scenario violates the schema contract."""


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ScenarioError(f"Missing required field {context}.{key}")
    return mapping[key]


def _positive(value: Any, context: str, allow_zero: bool = False) -> float:
    number = float(value)
    if number < 0 or (number == 0 and not allow_zero):
        relation = "non-negative" if allow_zero else "positive"
        raise ScenarioError(f"{context} must be {relation}")
    return number


def load_scenario(path: str | Path) -> Scenario:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    if not isinstance(raw, dict):
        raise ScenarioError("Scenario root must be a mapping")

    schema_version = str(_require(raw, "schema_version", "scenario"))
    if schema_version != "0.1":
        raise ScenarioError(f"Unsupported schema_version {schema_version!r}; expected '0.1'")

    world_raw = _require(raw, "world", "scenario")
    bounds_raw = _require(world_raw, "bounds", "world")
    world = Bounds2D(
        x_min=float(_require(bounds_raw, "x_min", "world.bounds")),
        x_max=float(_require(bounds_raw, "x_max", "world.bounds")),
        y_min=float(_require(bounds_raw, "y_min", "world.bounds")),
        y_max=float(_require(bounds_raw, "y_max", "world.bounds")),
    )
    if world.x_min >= world.x_max or world.y_min >= world.y_max:
        raise ScenarioError("World bounds must have increasing min/max values")

    materials: dict[str, Material] = {}
    for name, config in _require(raw, "materials", "scenario").items():
        materials[str(name)] = Material(
            name=str(name),
            linear_attenuation_per_m=_positive(
                _require(config, "linear_attenuation_per_m", f"materials.{name}"),
                f"materials.{name}.linear_attenuation_per_m",
                allow_zero=True,
            ),
        )

    obstacles = []
    obstacle_ids: set[str] = set()
    for index, config in enumerate(world_raw.get("obstacles", [])):
        obstacle = Obstacle(
            obstacle_id=str(_require(config, "id", f"world.obstacles[{index}]")),
            x_min=float(_require(config, "x_min", f"world.obstacles[{index}]")),
            x_max=float(_require(config, "x_max", f"world.obstacles[{index}]")),
            y_min=float(_require(config, "y_min", f"world.obstacles[{index}]")),
            y_max=float(_require(config, "y_max", f"world.obstacles[{index}]")),
            material=str(_require(config, "material", f"world.obstacles[{index}]")),
        )
        if obstacle.obstacle_id in obstacle_ids:
            raise ScenarioError(f"Duplicate obstacle id {obstacle.obstacle_id!r}")
        obstacle_ids.add(obstacle.obstacle_id)
        if obstacle.material not in materials:
            raise ScenarioError(f"Obstacle {obstacle.obstacle_id!r} uses unknown material")
        if obstacle.x_min >= obstacle.x_max or obstacle.y_min >= obstacle.y_max:
            raise ScenarioError(f"Obstacle {obstacle.obstacle_id!r} has invalid bounds")
        if not world.contains(obstacle.x_min, obstacle.y_min) or not world.contains(
            obstacle.x_max, obstacle.y_max
        ):
            raise ScenarioError(f"Obstacle {obstacle.obstacle_id!r} lies outside the world")
        obstacles.append(obstacle)

    sources = []
    source_ids: set[str] = set()
    for index, config in enumerate(_require(raw, "sources", "scenario")):
        source = RadiationSource(
            source_id=str(_require(config, "id", f"sources[{index}]")),
            x=float(_require(config, "x", f"sources[{index}]")),
            y=float(_require(config, "y", f"sources[{index}]")),
            reference_cps_at_1m=_positive(
                _require(config, "reference_cps_at_1m", f"sources[{index}]"),
                f"sources[{index}].reference_cps_at_1m",
            ),
            isotope=str(config.get("isotope", "unspecified")),
        )
        if source.source_id in source_ids:
            raise ScenarioError(f"Duplicate source id {source.source_id!r}")
        source_ids.add(source.source_id)
        if not world.contains(source.x, source.y):
            raise ScenarioError(f"Source {source.source_id!r} lies outside the world")
        sources.append(source)
    if not sources:
        raise ScenarioError("At least one radiation source is required")

    detector_raw = _require(raw, "detector", "scenario")
    detector = DetectorConfig(
        integration_time_s=_positive(
            _require(detector_raw, "integration_time_s", "detector"),
            "detector.integration_time_s",
        ),
        background_cps=_positive(
            _require(detector_raw, "background_cps", "detector"),
            "detector.background_cps",
            allow_zero=True,
        ),
        efficiency=_positive(detector_raw.get("efficiency", 1.0), "detector.efficiency"),
        max_cps=(
            _positive(detector_raw["max_cps"], "detector.max_cps")
            if detector_raw.get("max_cps") is not None
            else None
        ),
        dead_time_s=_positive(
            detector_raw.get("dead_time_s", 0.0), "detector.dead_time_s", allow_zero=True
        ),
        min_distance_m=_positive(
            detector_raw.get("min_distance_m", 0.1), "detector.min_distance_m"
        ),
        directional_exponent=_positive(
            detector_raw.get("directional_exponent", 0.0),
            "detector.directional_exponent",
            allow_zero=True,
        ),
    )
    if detector.efficiency > 1.0:
        raise ScenarioError("detector.efficiency cannot exceed 1.0")

    robot_raw = _require(raw, "robot", "scenario")
    start_raw = _require(robot_raw, "start", "robot")
    robot = RobotConfig(
        start=Pose2D(
            x=float(_require(start_raw, "x", "robot.start")),
            y=float(_require(start_raw, "y", "robot.start")),
            yaw=float(start_raw.get("yaw", 0.0)),
        ),
        max_linear_velocity_mps=_positive(
            _require(robot_raw, "max_linear_velocity_mps", "robot"),
            "robot.max_linear_velocity_mps",
        ),
        max_angular_velocity_rps=_positive(
            _require(robot_raw, "max_angular_velocity_rps", "robot"),
            "robot.max_angular_velocity_rps",
        ),
    )
    if not world.contains(robot.start.x, robot.start.y):
        raise ScenarioError("Robot start lies outside the world")
    if any(obstacle.contains(robot.start.x, robot.start.y) for obstacle in obstacles):
        raise ScenarioError("Robot start lies inside an obstacle")

    task_raw = _require(raw, "task", "scenario")
    goal_raw = task_raw.get("goal")
    goal = None
    if goal_raw is not None:
        goal = (
            float(_require(goal_raw, "x", "task.goal")),
            float(_require(goal_raw, "y", "task.goal")),
        )
        if not world.contains(*goal):
            raise ScenarioError("Task goal lies outside the world")
    max_steps_raw = _require(task_raw, "max_steps", "task")
    if int(max_steps_raw) != max_steps_raw or int(max_steps_raw) <= 0:
        raise ScenarioError("task.max_steps must be a positive integer")
    task = TaskConfig(
        task_type=str(_require(task_raw, "type", "task")),
        max_steps=int(max_steps_raw),
        dose_budget=_positive(
            _require(task_raw, "dose_budget", "task"), "task.dose_budget"
        ),
        goal=goal,
        goal_tolerance_m=_positive(
            task_raw.get("goal_tolerance_m", 0.4), "task.goal_tolerance_m"
        ),
        localization_tolerance_m=_positive(
            task_raw.get("localization_tolerance_m", 0.75),
            "task.localization_tolerance_m",
        ),
    )

    return Scenario(
        schema_version=schema_version,
        scenario_id=str(_require(raw, "scenario_id", "scenario")),
        split=str(_require(raw, "split", "scenario")),
        seed=int(_require(raw, "seed", "scenario")),
        time_step_s=_positive(_require(raw, "time_step_s", "scenario"), "time_step_s"),
        world=world,
        materials=materials,
        obstacles=tuple(obstacles),
        sources=tuple(sources),
        detector=detector,
        robot=robot,
        task=task,
        metadata=dict(raw.get("metadata", {})),
    )
