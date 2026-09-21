from __future__ import annotations

from dataclasses import asdict
from math import hypot

import numpy as np

from .detector import CountRateDetector
from .models import Action, EpisodeState, Observation, Pose2D, Scenario
from .physics import GammaField


class RadFieldEnv:
    """Minimal closed-loop benchmark environment with hidden radiation truth."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.field = GammaField(scenario)
        self.rng = np.random.default_rng(scenario.seed)
        self.detector = CountRateDetector(scenario.detector, self.field, self.rng)
        self.state = EpisodeState(pose=scenario.robot.start)
        self.history: list[dict[str, object]] = []

    def reset(self, seed: int | None = None) -> Observation:
        actual_seed = self.scenario.seed if seed is None else seed
        self.rng = np.random.default_rng(actual_seed)
        self.detector = CountRateDetector(self.scenario.detector, self.field, self.rng)
        self.state = EpisodeState(pose=self.scenario.robot.start)
        self.history = []
        return self._observe()

    def _observe(self) -> Observation:
        counts, measured_cps, expected_cps = self.detector.sample(self.state.pose)
        observation = Observation(
            step=self.state.step,
            time_s=self.state.time_s,
            pose=self.state.pose,
            counts=counts,
            count_rate_cps=measured_cps,
            cumulative_exposure=self.state.cumulative_exposure,
            remaining_exposure_budget=max(
                0.0, self.scenario.task.dose_budget - self.state.cumulative_exposure
            ),
        )
        self.state.peak_count_rate_cps = max(
            self.state.peak_count_rate_cps, measured_cps
        )
        self.history.append(
            {
                **asdict(observation),
                "pose": asdict(observation.pose),
                "expected_count_rate_cps": expected_cps,
            }
        )
        return observation

    def _collides(self, pose: Pose2D) -> bool:
        if not self.scenario.world.contains(pose.x, pose.y):
            return True
        return any(obstacle.contains(pose.x, pose.y) for obstacle in self.scenario.obstacles)

    def step(self, action: Action) -> tuple[Observation, float, bool, bool, dict[str, object]]:
        if self.state.terminated or self.state.truncated:
            raise RuntimeError("Episode has ended; call reset() before step()")

        linear = float(
            np.clip(
                action.linear_velocity_mps,
                -self.scenario.robot.max_linear_velocity_mps,
                self.scenario.robot.max_linear_velocity_mps,
            )
        )
        angular = float(
            np.clip(
                action.angular_velocity_rps,
                -self.scenario.robot.max_angular_velocity_rps,
                self.scenario.robot.max_angular_velocity_rps,
            )
        )
        candidate = self.state.pose.advanced(linear, angular, self.scenario.time_step_s)
        collision = self._collides(candidate)
        if collision:
            self.state.collision_count += 1
        else:
            self.state.pose = candidate

        self.state.step += 1
        self.state.time_s += self.scenario.time_step_s
        local_rate = self.field.expected_detector_cps(self.state.pose)
        self.state.cumulative_exposure += local_rate * self.scenario.time_step_s

        dose_exceeded = self.state.cumulative_exposure > self.scenario.task.dose_budget
        if dose_exceeded:
            self.state.terminated = True
            self.state.failure_reason = "dose_budget_exceeded"
        if self.scenario.task.goal is not None and not dose_exceeded:
            goal_x, goal_y = self.scenario.task.goal
            if hypot(self.state.pose.x - goal_x, self.state.pose.y - goal_y) <= self.scenario.task.goal_tolerance_m:
                self.state.terminated = True
                self.state.success = True
        if self.state.step >= self.scenario.task.max_steps and not self.state.terminated:
            self.state.truncated = True
            self.state.failure_reason = "max_steps"

        observation = self._observe()
        reward = -self.scenario.time_step_s - 0.001 * local_rate
        if collision:
            reward -= 5.0
        if self.state.success:
            reward += 100.0
        info = {
            "collision": collision,
            "success": self.state.success,
            "failure_reason": self.state.failure_reason,
        }
        return observation, reward, self.state.terminated, self.state.truncated, info
