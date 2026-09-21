from __future__ import annotations

import numpy as np

from .models import DetectorConfig, Pose2D
from .physics import GammaField


class CountRateDetector:
    def __init__(self, config: DetectorConfig, field: GammaField, rng: np.random.Generator):
        self.config = config
        self.field = field
        self.rng = rng

    def sample(self, pose: Pose2D) -> tuple[int, float, float]:
        expected_cps = self.field.expected_detector_cps(pose)
        expected_counts = expected_cps * self.config.integration_time_s
        counts = int(self.rng.poisson(expected_counts))
        measured_cps = counts / self.config.integration_time_s
        return counts, measured_cps, expected_cps

