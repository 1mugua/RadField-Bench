from __future__ import annotations

from dataclasses import asdict
from math import hypot, pi

import numpy as np

from .detector import CountRateDetector
from .models import Action, EpisodeState, Observation, Pose2D, Scenario
from .physics import GammaField


def _wrap_angle(angle: float) -> float:
    return (angle + pi) % (2.0 * pi) - pi


class RadFieldEnv:
    """Minimal closed-loop benchmark environment with hidden radiation truth."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.field = GammaField(scenario)
        self.rng = np.random.default_rng(scenario.seed)
        self.detector = CountRateDetector(scenario.detector, self.field, self.rng)
        self.state = EpisodeState(
            pose=scenario.robot.start, estimated_pose=scenario.robot.start
        )
        self._last_real_pose = scenario.robot.start
        self.history: list[dict[str, object]] = []

    def reset(self, seed: int | None = None) -> Observation:
        actual_seed = self.scenario.seed if seed is None else seed
        self.rng = np.random.default_rng(actual_seed)
        self.detector = CountRateDetector(self.scenario.detector, self.field, self.rng)
        self.state = EpisodeState(
            pose=self.scenario.robot.start, estimated_pose=self.scenario.robot.start
        )
        self._last_real_pose = self.scenario.robot.start
        self.history = []
        return self._observe()

    def _observe(self) -> Observation:
        counts, measured_cps, expected_cps = self.detector.sample(self.state.pose)
        if self.scenario.robot.pose_mode == "noisy_odometry":
            self._update_odometry_estimate()
            pose_estimate = self.state.estimated_pose
            pose_covariance = (
                self.scenario.robot.translation_noise_std_m ** 2,
                self.scenario.robot.translation_noise_std_m ** 2,
                self.scenario.robot.rotation_noise_std_rad ** 2,
            )
        else:
            pose_estimate = self.state.pose
            pose_covariance = (0.0, 0.0, 0.0)
        observation = Observation(
            schema_version="0.1",
            step=self.state.step,
            time_s=self.state.time_s,
            pose_estimate=pose_estimate,
            pose_covariance=pose_covariance,
            counts=counts,
            count_rate_cps=measured_cps,
            integration_time_s=self.scenario.detector.integration_time_s,
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
                "pose_estimate": asdict(pose_estimate),
                "pose_covariance": list(pose_covariance),
                "real_pose": asdict(self.state.pose),
                "expected_count_rate_cps": expected_cps,
            }
        )
        return observation

    def _update_odometry_estimate(self) -> None:
        real = self.state.pose
        previous_real = self._last_real_pose
        dx = real.x - previous_real.x
        dy = real.y - previous_real.y
        dyaw = _wrap_angle(real.yaw - previous_real.yaw)
        noisy_dx = dx + float(
            self.rng.normal(0.0, self.scenario.robot.translation_noise_std_m)
        )
        noisy_dy = dy + float(
            self.rng.normal(0.0, self.scenario.robot.translation_noise_std_m)
        )
        noisy_dyaw = dyaw + float(
            self.rng.normal(0.0, self.scenario.robot.rotation_noise_std_rad)
        )
        estimate = self.state.estimated_pose
        self.state.estimated_pose = Pose2D(
            x=estimate.x + noisy_dx,
            y=estimate.y + noisy_dy,
            yaw=_wrap_angle(estimate.yaw + noisy_dyaw),
        )
        self._last_real_pose = real

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
