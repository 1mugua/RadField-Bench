from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, sin
from typing import Any


@dataclass(frozen=True)
class Bounds2D:
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    yaw: float = 0.0

    def advanced(self, linear_velocity: float, angular_velocity: float, dt: float) -> "Pose2D":
        yaw = self.yaw + angular_velocity * dt
        return Pose2D(
            x=self.x + linear_velocity * cos(yaw) * dt,
            y=self.y + linear_velocity * sin(yaw) * dt,
            yaw=yaw,
        )


@dataclass(frozen=True)
class Material:
    name: str
    linear_attenuation_per_m: float


@dataclass(frozen=True)
class Obstacle:
    obstacle_id: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    material: str

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


@dataclass(frozen=True)
class RadiationSource:
    source_id: str
    x: float
    y: float
    reference_cps_at_1m: float
    isotope: str = "unspecified"


@dataclass(frozen=True)
class DetectorConfig:
    integration_time_s: float
    background_cps: float
    efficiency: float = 1.0
    max_cps: float | None = None
    dead_time_s: float = 0.0
    min_distance_m: float = 0.1
    directional_exponent: float = 0.0


@dataclass(frozen=True)
class RobotConfig:
    start: Pose2D
    max_linear_velocity_mps: float
    max_angular_velocity_rps: float


@dataclass(frozen=True)
class TaskConfig:
    task_type: str
    max_steps: int
    dose_budget: float
    goal: tuple[float, float] | None = None
    goal_tolerance_m: float = 0.4
    localization_tolerance_m: float = 0.75


@dataclass(frozen=True)
class Scenario:
    schema_version: str
    scenario_id: str
    split: str
    seed: int
    time_step_s: float
    world: Bounds2D
    materials: dict[str, Material]
    obstacles: tuple[Obstacle, ...]
    sources: tuple[RadiationSource, ...]
    detector: DetectorConfig
    robot: RobotConfig
    task: TaskConfig
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    linear_velocity_mps: float
    angular_velocity_rps: float = 0.0


@dataclass(frozen=True)
class Observation:
    step: int
    time_s: float
    pose: Pose2D
    counts: int
    count_rate_cps: float
    cumulative_exposure: float
    remaining_exposure_budget: float


@dataclass
class EpisodeState:
    pose: Pose2D
    step: int = 0
    time_s: float = 0.0
    cumulative_exposure: float = 0.0
    peak_count_rate_cps: float = 0.0
    collision_count: int = 0
    terminated: bool = False
    truncated: bool = False
    success: bool = False
    failure_reason: str | None = None

