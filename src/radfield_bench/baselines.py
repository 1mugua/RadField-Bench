from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import atan2, pi

import numpy as np

from .models import Action, Bounds2D, Observation, Scenario


def wrap_angle(angle: float) -> float:
    return (angle + pi) % (2.0 * pi) - pi


class BaselineAgent(ABC):
    @abstractmethod
    def reset(self, scenario: Scenario, seed: int | None = None) -> None:
        pass

    @abstractmethod
    def act(self, observation: Observation) -> Action:
        pass

    def estimate(self) -> dict[str, object]:
        return {}


@dataclass
class _Measurement:
    x: float
    y: float
    cps: float


class RandomWalkAgent(BaselineAgent):
    def reset(self, scenario: Scenario, seed: int | None = None) -> None:
        self.scenario = scenario
        actual_seed = scenario.seed if seed is None else seed
        self.rng = np.random.default_rng(actual_seed + 10_001)
        self.measurements: list[_Measurement] = []

    def act(self, observation: Observation) -> Action:
        self.measurements.append(
            _Measurement(observation.pose.x, observation.pose.y, observation.count_rate_cps)
        )
        angular = float(self.rng.normal(0.0, 0.55))
        return Action(self.scenario.robot.max_linear_velocity_mps * 0.65, angular)

    def estimate(self) -> dict[str, object]:
        return _max_measurement_estimate(self.measurements)


class LawnmowerAgent(BaselineAgent):
    """Deterministic coverage baseline with a simple point controller."""

    def reset(self, scenario: Scenario, seed: int | None = None) -> None:
        self.scenario = scenario
        self.measurements: list[_Measurement] = []
        self.waypoints = _coverage_waypoints(scenario.world, spacing=1.0, margin=0.5)
        self.index = 0

    def act(self, observation: Observation) -> Action:
        self.measurements.append(
            _Measurement(observation.pose.x, observation.pose.y, observation.count_rate_cps)
        )
        if not self.waypoints:
            return Action(0.0, 0.0)
        while self.index < len(self.waypoints) - 1:
            target_x, target_y = self.waypoints[self.index]
            if (target_x - observation.pose.x) ** 2 + (target_y - observation.pose.y) ** 2 < 0.18**2:
                self.index += 1
            else:
                break
        target_x, target_y = self.waypoints[self.index]
        target_yaw = atan2(target_y - observation.pose.y, target_x - observation.pose.x)
        error = wrap_angle(target_yaw - observation.pose.yaw)
        angular = float(
            np.clip(
                2.0 * error,
                -self.scenario.robot.max_angular_velocity_rps,
                self.scenario.robot.max_angular_velocity_rps,
            )
        )
        speed_scale = max(0.0, 1.0 - abs(error) / (pi / 2.0))
        linear = self.scenario.robot.max_linear_velocity_mps * speed_scale
        return Action(linear, angular)

    def estimate(self) -> dict[str, object]:
        return _max_measurement_estimate(self.measurements)


class BayesianGridAgent(BaselineAgent):
    """Single-source Bayesian grid baseline with explicit model mismatch."""

    def reset(self, scenario: Scenario, seed: int | None = None) -> None:
        self.scenario = scenario
        self.measurements: list[_Measurement] = []
        self.grid = _grid_points(scenario, spacing=0.5, margin=0.35)
        self.log_posterior = np.zeros(len(self.grid), dtype=float)
        self.assumed_reference_cps_at_1m = 150.0

    def act(self, observation: Observation) -> Action:
        self.measurements.append(
            _Measurement(observation.pose.x, observation.pose.y, observation.count_rate_cps)
        )
        counts = float(observation.counts)
        dt = self.scenario.detector.integration_time_s
        for index, (x, y) in enumerate(self.grid):
            distance = max(
                ((x - observation.pose.x) ** 2 + (y - observation.pose.y) ** 2) ** 0.5,
                self.scenario.detector.min_distance_m,
            )
            expected_cps = self.scenario.detector.background_cps + (
                self.scenario.detector.efficiency
                * self.assumed_reference_cps_at_1m
                / (distance * distance)
            )
            expected_counts = max(expected_cps * dt, 1e-9)
            self.log_posterior[index] += counts * np.log(expected_counts) - expected_counts
        self.log_posterior -= np.max(self.log_posterior)
        target_x, target_y = self.grid[int(np.argmax(self.log_posterior))]
        target_yaw = atan2(target_y - observation.pose.y, target_x - observation.pose.x)
        error = wrap_angle(target_yaw - observation.pose.yaw)
        angular = float(
            np.clip(
                2.0 * error,
                -self.scenario.robot.max_angular_velocity_rps,
                self.scenario.robot.max_angular_velocity_rps,
            )
        )
        speed_scale = max(0.0, 1.0 - abs(error) / (pi / 2.0))
        return Action(self.scenario.robot.max_linear_velocity_mps * speed_scale, angular)

    def estimate(self) -> dict[str, object]:
        if not self.grid:
            return {"method": "bayesian_grid_single_source", "source_estimates": []}
        index = int(np.argmax(self.log_posterior))
        posterior = np.exp(self.log_posterior - np.max(self.log_posterior))
        posterior = posterior / np.sum(posterior)
        return {
            "method": "bayesian_grid_single_source",
            "source_estimates": [
                {
                    "x": self.grid[index][0],
                    "y": self.grid[index][1],
                    "confidence": float(posterior[index]),
                    "observed_cps": None,
                }
            ],
        }


def _coverage_waypoints(
    bounds: Bounds2D, spacing: float, margin: float
) -> list[tuple[float, float]]:
    xs = np.arange(bounds.x_min + margin, bounds.x_max - margin + 1e-9, spacing)
    ys = np.arange(bounds.y_min + margin, bounds.y_max - margin + 1e-9, spacing)
    waypoints: list[tuple[float, float]] = []
    for row, y in enumerate(ys):
        row_xs = xs if row % 2 == 0 else xs[::-1]
        waypoints.extend((float(x), float(y)) for x in row_xs)
    return waypoints


def _grid_points(scenario: Scenario, spacing: float, margin: float) -> list[tuple[float, float]]:
    xs = np.arange(
        scenario.world.x_min + margin,
        scenario.world.x_max - margin + 1e-9,
        spacing,
    )
    ys = np.arange(
        scenario.world.y_min + margin,
        scenario.world.y_max - margin + 1e-9,
        spacing,
    )
    return [
        (float(x), float(y))
        for y in ys
        for x in xs
        if not any(obstacle.contains(float(x), float(y)) for obstacle in scenario.obstacles)
    ]


def _max_measurement_estimate(measurements: list[_Measurement]) -> dict[str, object]:
    if not measurements:
        return {"source_estimates": []}
    best = max(measurements, key=lambda measurement: measurement.cps)
    return {
        "method": "maximum_observed_count_rate",
        "source_estimates": [
            {"x": best.x, "y": best.y, "confidence": None, "observed_cps": best.cps}
        ],
    }


def make_baseline(name: str) -> BaselineAgent:
    normalized = name.strip().lower()
    if normalized == "random":
        return RandomWalkAgent()
    if normalized == "lawnmower":
        return LawnmowerAgent()
    if normalized in {"bayes", "bayes-grid", "bayesian-grid"}:
        return BayesianGridAgent()
    raise ValueError(
        f"Unknown baseline {name!r}; choose from: random, lawnmower, bayes-grid"
    )
