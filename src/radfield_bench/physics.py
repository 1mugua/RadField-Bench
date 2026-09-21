from __future__ import annotations

from math import atan2, cos, exp, hypot

from .geometry import segment_length_inside_rectangle
from .models import Pose2D, Scenario


class GammaField:
    """Lightweight real-time gamma count-rate approximation.

    The model is intentionally limited to inverse-square point sources with
    exponential attenuation through axis-aligned obstacles. It is suitable for
    algorithm benchmarking, not radiation-protection calculations.
    """

    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def source_rate_at(self, pose: Pose2D, source_index: int) -> float:
        source = self.scenario.sources[source_index]
        detector = self.scenario.detector
        distance = max(hypot(source.x - pose.x, source.y - pose.y), detector.min_distance_m)
        rate = source.reference_cps_at_1m / (distance * distance)

        attenuation_exponent = 0.0
        for obstacle in self.scenario.obstacles:
            path_length = segment_length_inside_rectangle(
                source.x, source.y, pose.x, pose.y, obstacle
            )
            attenuation_exponent += (
                self.scenario.materials[obstacle.material].linear_attenuation_per_m
                * path_length
            )
        rate *= exp(-attenuation_exponent)

        if detector.directional_exponent > 0.0:
            bearing = atan2(source.y - pose.y, source.x - pose.x)
            response = max(0.0, cos(bearing - pose.yaw)) ** detector.directional_exponent
            rate *= response
        return rate

    def expected_source_cps(self, pose: Pose2D) -> float:
        return sum(self.source_rate_at(pose, index) for index in range(len(self.scenario.sources)))

    def expected_detector_cps(self, pose: Pose2D) -> float:
        detector = self.scenario.detector
        incident = self.expected_source_cps(pose) * detector.efficiency + detector.background_cps
        if detector.dead_time_s > 0.0:
            incident = incident / (1.0 + incident * detector.dead_time_s)
        if detector.max_cps is not None:
            incident = min(incident, detector.max_cps)
        return max(0.0, incident)

