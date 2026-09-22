"""Domain templates for the RadField-Bench scenario library.

Scenarios are organized by real-world nuclear/business domains, not by
ML-style train/validation/test splits. Each domain contains scenario
families; each family is instantiated at three difficulty levels
(simple / medium / hard), and each difficulty level can be instantiated
multiple times (instances) with different seeds to give statistical meaning.

Current domains (v0.1 of the domain library):
  - npp_patrol          nuclear power plant site patrol / hot-spot checking
  - source_search       lost / hidden radioactive source search
  - security_screening  public venue radiation security screening
  - waste_management    nuclear waste store patrol and decommissioning survey
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from ..models import (
    Bounds2D,
    DetectorConfig,
    Material,
    Obstacle,
    Pose2D,
    RadiationSource,
    RobotConfig,
    TaskConfig,
)

DIFFICULTIES = ("simple", "medium", "hard")

# Shared material table. Linear attenuation coefficients are synthetic
# benchmark values (per metre), consistent with the existing reference
# scenarios; they are not certified radiation-transport data.
AIR = Material(name="air", linear_attenuation_per_m=0.0)
CONCRETE = Material(name="concrete", linear_attenuation_per_m=0.4)
STEEL = Material(name="steel", linear_attenuation_per_m=1.2)

MATERIALS: tuple[Material, ...] = (AIR, CONCRETE, STEEL)
MATERIAL_MAP: dict[str, Material] = {m.name: m for m in MATERIALS}


def _material(name: str) -> Material:
    return MATERIAL_MAP[name]


def _obstacle(obstacle_id: str, x_min: float, x_max: float, y_min: float, y_max: float, material: str) -> Obstacle:
    return Obstacle(obstacle_id=obstacle_id, x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max, material=material)


def _uniform_pose(
    rng: np.random.Generator, bounds: Bounds2D, margin: float = 0.6
) -> tuple[float, float]:
    x = float(rng.uniform(bounds.x_min + margin, bounds.x_max - margin))
    y = float(rng.uniform(bounds.y_min + margin, bounds.y_max - margin))
    return x, y


def _place_sources_outside_obstacles(
    rng: np.random.Generator,
    bounds: Bounds2D,
    obstacles: tuple[Obstacle, ...],
    strengths: list[float],
    margin: float = 0.6,
) -> tuple[RadiationSource, ...]:
    sources: list[RadiationSource] = []
    for index, strength in enumerate(strengths):
        for _attempt in range(200):
            x, y = _uniform_pose(rng, bounds, margin)
            pose_ok = True
            for obstacle in obstacles:
                if obstacle.contains(x, y):
                    pose_ok = False
                    break
            if pose_ok:
                sources.append(
                    RadiationSource(
                        source_id=f"source_{index + 1:02d}",
                        x=x,
                        y=y,
                        reference_cps_at_1m=float(strength),
                        isotope="synthetic_gamma",
                    )
                )
                break
        else:
            raise RuntimeError("could not place source outside obstacles")
    return tuple(sources)


def _robot_config(difficulty: str) -> RobotConfig:
    noise = {
        "simple": (0.01, 0.01),
        "medium": (0.02, 0.02),
        "hard": (0.03, 0.03),
    }[difficulty]
    return RobotConfig(
        start=Pose2D(x=1.0, y=1.0, yaw=0.0),
        max_linear_velocity_mps=0.7,
        max_angular_velocity_rps=1.0,
        pose_mode="noisy_odometry",
        translation_noise_std_m=noise[0],
        rotation_noise_std_rad=noise[1],
    )


@dataclass(frozen=True)
class FamilySpec:
    """One scenario family: a business layout template parameterized by difficulty."""

    domain: str
    family: str
    description: str
    materials: tuple[Material, ...]
    world: Callable[[np.random.Generator, str], tuple[Bounds2D, tuple[Obstacle, ...]]]
    sources: Callable[[np.random.Generator, str, tuple[Obstacle, ...]], tuple[RadiationSource, ...]]
    detector: Callable[[str], DetectorConfig]
    robot: Callable[[str], RobotConfig]
    task: Callable[[str], TaskConfig]

    @property
    def domain_description(self) -> str:
        return DOMAIN_DESCRIPTIONS[self.domain]


DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "npp_patrol": "Nuclear power plant site patrol: periodic walk-through, hot-spot and leak checking.",
    "source_search": "Lost or hidden radioactive source search and recovery.",
    "security_screening": "Public venue radiation security screening (station, cargo).",
    "waste_management": "Nuclear waste store patrol and decommissioning survey under tight exposure budget.",
}


# ---------------------------------------------------------------------------
# Domain 1: nuclear power plant patrol (npp_patrol)
# ---------------------------------------------------------------------------

def _world_reactor_corridor(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=12.0, y_min=0.0, y_max=5.0)
    obstacles: list[Obstacle] = []
    # equipment cabinets along both walls
    for i in range(4):
        obstacles.append(
            _obstacle(f"cabinet_l{i}", x_min=1.0 + i * 2.8, x_max=1.0 + i * 2.8 + 1.2, y_min=0.2, y_max=0.9, material="steel")
        )
        obstacles.append(
            _obstacle(f"cabinet_r{i}", x_min=1.0 + i * 2.8, x_max=1.0 + i * 2.8 + 1.2, y_min=4.1, y_max=4.8, material="steel")
        )
    if difficulty in ("medium", "hard"):
        obstacles.append(_obstacle("wall_1", x_min=5.4, x_max=5.9, y_min=1.2, y_max=3.8, material="concrete"))
    if difficulty == "hard":
        obstacles.append(_obstacle("wall_2", x_min=9.0, x_max=9.4, y_min=0.0, y_max=3.2, material="concrete"))
    return bounds, tuple(obstacles)


def _sources_reactor_corridor(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 12.0, 0.0, 5.0)
    strengths = {
        "simple": [150.0],
        "medium": [130.0, 180.0],
        "hard": [60.0, 120.0, 200.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


def _detector_npp(difficulty: str) -> DetectorConfig:
    background = {"simple": 15.0, "medium": 25.0, "hard": 35.0}[difficulty]
    return DetectorConfig(
        integration_time_s=0.5,
        background_cps=background,
        efficiency=0.85,
        max_cps=5000.0,
        dead_time_s=0.00002,
        min_distance_m=0.25,
        directional_exponent=0.0,
    )


def _task_patrol(difficulty: str) -> TaskConfig:
    spec = {
        "simple": dict(max_steps=320, dose_budget=900.0, goal=(11.0, 4.0)),
        "medium": dict(max_steps=420, dose_budget=800.0, goal=(11.0, 4.0)),
        "hard": dict(max_steps=520, dose_budget=700.0, goal=(11.0, 4.0)),
    }[difficulty]
    return TaskConfig(
        task_type="safe_exploration",
        max_steps=spec["max_steps"],
        dose_budget=spec["dose_budget"],
        goal=spec["goal"],
        goal_tolerance_m=0.5,
        localization_tolerance_m=1.0,
    )


def _task_pump_hall(difficulty: str) -> TaskConfig:
    spec = {
        "simple": dict(max_steps=320, dose_budget=900.0),
        "medium": dict(max_steps=420, dose_budget=800.0),
        "hard": dict(max_steps=520, dose_budget=700.0),
    }[difficulty]
    return TaskConfig(
        task_type="safe_exploration",
        max_steps=spec["max_steps"],
        dose_budget=spec["dose_budget"],
        goal=(9.0, 7.0),
        goal_tolerance_m=0.5,
        localization_tolerance_m=1.0,
    )


def _world_pump_hall(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=10.0, y_min=0.0, y_max=8.0)
    obstacles: list[Obstacle] = []
    # two longitudinal partition walls with openings (three bays)
    obstacles.append(_obstacle("partition_1", x_min=3.2, x_max=3.6, y_min=0.0, y_max=3.0, material="concrete"))
    obstacles.append(_obstacle("partition_1b", x_min=3.2, x_max=3.6, y_min=5.0, y_max=8.0, material="concrete"))
    if difficulty in ("medium", "hard"):
        obstacles.append(_obstacle("partition_2", x_min=6.8, x_max=7.2, y_min=0.0, y_max=3.4, material="concrete"))
        obstacles.append(_obstacle("partition_2b", x_min=6.8, x_max=7.2, y_min=4.6, y_max=8.0, material="concrete"))
    # pump blocks
    for bay, y_base in ((0, 4.2), (1, 4.2)):
        obstacles.append(
            _obstacle(f"pump_{bay}", x_min=1.0 + bay * 3.6, x_max=2.2 + bay * 3.6, y_min=3.5, y_max=4.5, material="steel")
        )
    return bounds, tuple(obstacles)


def _sources_pump_hall(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 10.0, 0.0, 8.0)
    strengths = {
        "simple": [150.0],
        "medium": [140.0, 190.0],
        "hard": [90.0, 160.0, 210.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


# ---------------------------------------------------------------------------
# Domain 2: radioactive source search (source_search)
# ---------------------------------------------------------------------------

def _world_open_area(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=14.0, y_min=0.0, y_max=10.0)
    obstacles: list[Obstacle] = []
    if difficulty != "simple":
        # scattered low obstacles (crates / vehicles)
        for i in range(4):
            x = float(rng.uniform(1.5, 12.0))
            y = float(rng.uniform(1.5, 8.0))
            obstacles.append(
                _obstacle(f"crate_{i}", x_min=x, x_max=x + 1.0, y_min=y, y_max=y + 0.8, material="steel")
            )
    return bounds, tuple(obstacles)


def _sources_open_area(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 14.0, 0.0, 10.0)
    strengths = {
        "simple": [250.0],
        "medium": [90.0],
        "hard": [280.0, 70.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


def _detector_search(difficulty: str) -> DetectorConfig:
    background = {"simple": 3.0, "medium": 6.0, "hard": 10.0}[difficulty]
    return DetectorConfig(
        integration_time_s=0.5,
        background_cps=background,
        efficiency=0.9,
        max_cps=5000.0,
        dead_time_s=0.00002,
        min_distance_m=0.25,
        directional_exponent=0.0,
    )


def _task_localize(difficulty: str) -> TaskConfig:
    spec = {
        "simple": dict(max_steps=300, dose_budget=950.0, tolerance=1.2),
        "medium": dict(max_steps=360, dose_budget=900.0, tolerance=1.0),
        "hard": dict(max_steps=460, dose_budget=850.0, tolerance=1.0),
    }[difficulty]
    return TaskConfig(
        task_type="source_localization",
        max_steps=spec["max_steps"],
        dose_budget=spec["dose_budget"],
        localization_tolerance_m=spec["tolerance"],
    )


def _world_shielded_hiding(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=12.0, y_min=0.0, y_max=8.0)
    obstacles: list[Obstacle] = [
        _obstacle("column_1", x_min=4.0, x_max=4.5, y_min=2.0, y_max=6.0, material="concrete"),
    ]
    if difficulty in ("medium", "hard"):
        obstacles.append(_obstacle("steel_cabinet", x_min=8.0, x_max=9.0, y_min=1.5, y_max=2.2, material="steel"))
    return bounds, tuple(obstacles)


def _sources_shielded_hiding(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 12.0, 0.0, 8.0)
    strengths = {
        "simple": [220.0],
        "medium": [260.0],
        "hard": [300.0, 120.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


# ---------------------------------------------------------------------------
# Domain 3: public venue security screening (security_screening)
# ---------------------------------------------------------------------------

def _world_station_hall(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=16.0, y_min=0.0, y_max=10.0)
    obstacles: list[Obstacle] = []
    # seating rows and pillars
    for i in range(5):
        x = 2.0 + i * 2.9
        obstacles.append(_obstacle(f"seat_{i}", x_min=x, x_max=x + 0.7, y_min=4.2, y_max=5.8, material="steel"))
    for j in range(3):
        y = 1.5 + j * 3.5
        obstacles.append(_obstacle(f"pillar_{j}", x_min=8.0, x_max=8.4, y_min=y, y_max=y + 0.5, material="concrete"))
    return bounds, tuple(obstacles)


def _sources_station_hall(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 16.0, 0.0, 10.0)
    strengths = {
        "simple": [80.0],
        "medium": [70.0],
        "hard": [90.0, 55.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


def _detector_screening(difficulty: str) -> DetectorConfig:
    background = {"simple": 5.0, "medium": 10.0, "hard": 20.0}[difficulty]
    return DetectorConfig(
        integration_time_s=0.4,
        background_cps=background,
        efficiency=0.8,
        max_cps=5000.0,
        dead_time_s=0.00002,
        min_distance_m=0.25,
        directional_exponent=1.0,
    )


def _task_screening(difficulty: str) -> TaskConfig:
    # Security screening has time pressure: fewer steps at harder levels.
    spec = {
        "simple": dict(max_steps=320, dose_budget=900.0, tolerance=1.0),
        "medium": dict(max_steps=280, dose_budget=850.0, tolerance=1.0),
        "hard": dict(max_steps=240, dose_budget=800.0, tolerance=1.0),
    }[difficulty]
    return TaskConfig(
        task_type="source_localization",
        max_steps=spec["max_steps"],
        dose_budget=spec["dose_budget"],
        localization_tolerance_m=spec["tolerance"],
    )


def _world_cargo_bay(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=14.0, y_min=0.0, y_max=9.0)
    obstacles: list[Obstacle] = [
        _obstacle("container_1", x_min=2.0, x_max=4.5, y_min=1.0, y_max=2.6, material="steel"),
        _obstacle("container_2", x_min=8.0, x_max=10.5, y_min=5.5, y_max=7.1, material="steel"),
    ]
    if difficulty in ("medium", "hard"):
        obstacles.append(_obstacle("rack", x_min=5.5, x_max=6.3, y_min=3.0, y_max=6.0, material="concrete"))
    return bounds, tuple(obstacles)


def _sources_cargo_bay(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 14.0, 0.0, 9.0)
    strengths = {
        "simple": [130.0],
        "medium": [160.0],
        "hard": [200.0, 85.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


# ---------------------------------------------------------------------------
# Domain 4: waste management (waste_management)
# ---------------------------------------------------------------------------

def _world_waste_store(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=12.0, y_min=0.0, y_max=10.0)
    obstacles: list[Obstacle] = []
    # drum array
    for i in range(5):
        for j in range(3):
            if (i + j) % 3 == 0:
                continue
            obstacles.append(
                _obstacle(
                    f"drum_{i}_{j}",
                    x_min=1.0 + i * 2.1,
                    x_max=1.0 + i * 2.1 + 1.0,
                    y_min=1.0 + j * 2.9,
                    y_max=1.0 + j * 2.9 + 1.0,
                    material="steel",
                )
            )
    if difficulty in ("medium", "hard"):
        obstacles.append(_obstacle("shield_wall", x_min=6.0, x_max=6.4, y_min=0.0, y_max=5.5, material="concrete"))
    return bounds, tuple(obstacles)


def _sources_waste_store(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 12.0, 0.0, 10.0)
    strengths = {
        "simple": [400.0],
        "medium": [500.0, 320.0],
        "hard": [800.0, 450.0, 300.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


def _detector_waste(difficulty: str) -> DetectorConfig:
    background = {"simple": 30.0, "medium": 50.0, "hard": 70.0}[difficulty]
    return DetectorConfig(
        integration_time_s=0.5,
        background_cps=background,
        efficiency=0.9,
        max_cps=8000.0,
        dead_time_s=0.00002,
        min_distance_m=0.25,
        directional_exponent=0.0,
    )


def _task_waste(difficulty: str) -> TaskConfig:
    # Waste management is dose-constrained: budget shrinks as levels rise.
    spec = {
        "simple": dict(max_steps=380, dose_budget=1000.0, goal=(11.0, 9.0)),
        "medium": dict(max_steps=460, dose_budget=800.0, goal=(11.0, 9.0)),
        "hard": dict(max_steps=560, dose_budget=600.0, goal=(11.0, 9.0)),
    }[difficulty]
    return TaskConfig(
        task_type="safe_exploration",
        max_steps=spec["max_steps"],
        dose_budget=spec["dose_budget"],
        goal=spec["goal"],
        goal_tolerance_m=0.5,
        localization_tolerance_m=1.0,
    )


def _world_decommissioning(rng: np.random.Generator, difficulty: str) -> tuple[Bounds2D, tuple[Obstacle, ...]]:
    bounds = Bounds2D(x_min=0.0, x_max=16.0, y_min=0.0, y_max=10.0)
    obstacles: list[Obstacle] = []
    for i in range(5):
        x = float(rng.uniform(1.5, 13.5))
        y = float(rng.uniform(1.5, 8.0))
        obstacles.append(
            _obstacle(
                f"debris_{i}",
                x_min=x,
                x_max=x + float(rng.uniform(0.8, 1.8)),
                y_min=y,
                y_max=y + float(rng.uniform(0.6, 1.4)),
                material="concrete",
            )
        )
    return bounds, tuple(obstacles)


def _sources_decommissioning(
    rng: np.random.Generator, difficulty: str, obstacles: tuple[Obstacle, ...]
) -> tuple[RadiationSource, ...]:
    bounds = Bounds2D(0.0, 16.0, 0.0, 10.0)
    strengths = {
        "simple": [250.0],
        "medium": [300.0, 150.0],
        "hard": [420.0, 260.0, 120.0],
    }[difficulty]
    return _place_sources_outside_obstacles(rng, bounds, obstacles, strengths, margin=1.0)


def _task_decommissioning(difficulty: str) -> TaskConfig:
    spec = {
        "simple": dict(max_steps=340, dose_budget=950.0, tolerance=1.2),
        "medium": dict(max_steps=440, dose_budget=850.0, tolerance=1.0),
        "hard": dict(max_steps=540, dose_budget=750.0, tolerance=1.0),
    }[difficulty]
    return TaskConfig(
        task_type="source_localization",
        max_steps=spec["max_steps"],
        dose_budget=spec["dose_budget"],
        localization_tolerance_m=spec["tolerance"],
    )


# ---------------------------------------------------------------------------
# Family registry
# ---------------------------------------------------------------------------

FAMILIES: tuple[FamilySpec, ...] = (
    # --- npp_patrol ---
    FamilySpec(
        domain="npp_patrol",
        family="reactor_corridor",
        description="Periodic patrol along a reactor pipe corridor; find and localize hot spots.",
        materials=MATERIALS,
        world=_world_reactor_corridor,
        sources=_sources_reactor_corridor,
        detector=_detector_npp,
        robot=_robot_config,
        task=_task_patrol,
    ),
    FamilySpec(
        domain="npp_patrol",
        family="pump_hall",
        description="Bay-by-bay patrol of a pump hall; check equipment hot spots across partitions.",
        materials=MATERIALS,
        world=_world_pump_hall,
        sources=_sources_pump_hall,
        detector=_detector_npp,
        robot=_robot_config,
        task=_task_pump_hall,
    ),
    # --- source_search ---
    FamilySpec(
        domain="source_search",
        family="open_area",
        description="Search an open yard for a lost source; recover and localize it.",
        materials=MATERIALS,
        world=_world_open_area,
        sources=_sources_open_area,
        detector=_detector_search,
        robot=_robot_config,
        task=_task_localize,
    ),
    FamilySpec(
        domain="source_search",
        family="shielded_hiding",
        description="Locate sources hidden behind or inside shielding structures.",
        materials=MATERIALS,
        world=_world_shielded_hiding,
        sources=_sources_shielded_hiding,
        detector=_detector_search,
        robot=_robot_config,
        task=_task_localize,
    ),
    # --- security_screening ---
    FamilySpec(
        domain="security_screening",
        family="station_hall",
        description="Screen a busy station hall for a hidden source under time pressure.",
        materials=MATERIALS,
        world=_world_station_hall,
        sources=_sources_station_hall,
        detector=_detector_screening,
        robot=_robot_config,
        task=_task_screening,
    ),
    FamilySpec(
        domain="security_screening",
        family="cargo_bay",
        description="Scan cargo in a bay for shielded smuggled sources.",
        materials=MATERIALS,
        world=_world_cargo_bay,
        sources=_sources_cargo_bay,
        detector=_detector_screening,
        robot=_robot_config,
        task=_task_screening,
    ),
    # --- waste_management ---
    FamilySpec(
        domain="waste_management",
        family="waste_store",
        description="Patrol a waste store with drum arrays under a tight exposure budget.",
        materials=MATERIALS,
        world=_world_waste_store,
        sources=_sources_waste_store,
        detector=_detector_waste,
        robot=_robot_config,
        task=_task_waste,
    ),
    FamilySpec(
        domain="waste_management",
        family="decommissioning_site",
        description="Survey a decommissioning site with scattered debris and residual hot spots.",
        materials=MATERIALS,
        world=_world_decommissioning,
        sources=_sources_decommissioning,
        detector=_detector_waste,
        robot=_robot_config,
        task=_task_decommissioning,
    ),
)

FAMILY_INDEX: dict[str, FamilySpec] = {
    f"{spec.domain}/{spec.family}": spec for spec in FAMILIES
}
