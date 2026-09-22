"""T0 Detector Sanity Check.

Validates the physics/detector model independently of any algorithm:
inverse-square law, material attenuation, Poisson statistics, dead time,
saturation, directional response, and seed reproducibility.
"""
import numpy as np

from radfield_bench.detector import CountRateDetector
from radfield_bench.geometry import segment_length_inside_rectangle
from radfield_bench.models import (
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
from radfield_bench.physics import GammaField


def make_scenario(**overrides) -> Scenario:
    defaults = dict(
        schema_version="0.1",
        scenario_id="sanity_check",
        split="train",
        seed=1,
        time_step_s=0.25,
        world=Bounds2D(x_min=0.0, x_max=10.0, y_min=0.0, y_max=10.0),
        materials={
            "air": Material(name="air", linear_attenuation_per_m=0.0),
            "concrete": Material(name="concrete", linear_attenuation_per_m=0.5),
        },
        obstacles=(),
        sources=(RadiationSource(source_id="s", x=5.0, y=5.0, reference_cps_at_1m=100.0),),
        detector=DetectorConfig(integration_time_s=1.0, background_cps=0.0),
        robot=RobotConfig(start=Pose2D(x=0.0, y=0.0), max_linear_velocity_mps=1.0, max_angular_velocity_rps=1.0),
        task=TaskConfig(task_type="source_localization", max_steps=100, dose_budget=1000.0),
    )
    defaults.update(overrides)
    return Scenario(**defaults)


def test_inverse_square_ratio_is_exactly_four():
    scenario = make_scenario()
    field = GammaField(scenario)
    source = scenario.sources[0]
    rate_1m = field.expected_detector_cps(Pose2D(source.x - 1.0, source.y))
    rate_2m = field.expected_detector_cps(Pose2D(source.x - 2.0, source.y))
    # No attenuation, no background: doubling distance quarters the rate.
    assert abs(rate_1m / rate_2m - 4.0) < 1e-9


def test_material_attenuation_matches_exponential_decay():
    wall = Obstacle(
        obstacle_id="wall",
        x_min=0.4,
        x_max=1.6,
        y_min=-0.5,
        y_max=0.5,
        material="concrete",
    )
    scenario = make_scenario(
        world=Bounds2D(-1.0, 3.0, -1.0, 1.0),
        sources=(RadiationSource(source_id="s", x=0.0, y=0.0, reference_cps_at_1m=100.0),),
        obstacles=(wall,),
    )
    field = GammaField(scenario)
    source = scenario.sources[0]
    detector_pose = Pose2D(x=2.0, y=0.0)

    mu = scenario.materials["concrete"].linear_attenuation_per_m
    path_inside = segment_length_inside_rectangle(
        source.x, source.y, detector_pose.x, detector_pose.y, wall
    )
    assert abs(path_inside - 1.2) < 1e-9

    blocked = field.expected_source_cps(detector_pose)
    unblocked = 100.0 / (2.0 ** 2)  # inverse square only, no material
    assert abs(blocked / unblocked - np.exp(-mu * path_inside)) < 1e-9


def test_poisson_counts_mean_and_variance():
    scenario = make_scenario(
        sources=(RadiationSource(source_id="s", x=5.0, y=5.0, reference_cps_at_1m=100.0),),
    )
    field = GammaField(scenario)
    # 1 m from a 100 cps source with integration 1 s -> expected 100 counts.
    rng = np.random.default_rng(42)
    detector = CountRateDetector(scenario.detector, field, rng)
    pose = Pose2D(x=4.0, y=5.0)
    samples = np.array([detector.sample(pose)[0] for _ in range(5000)], dtype=float)
    expected_counts = field.expected_detector_cps(pose) * scenario.detector.integration_time_s
    mean = samples.mean()
    variance = samples.var()
    # Poisson: variance ~= mean ~= expected counts (10% tolerance for 5000 draws).
    assert abs(mean - expected_counts) < 0.1 * expected_counts
    assert abs(variance - expected_counts) < 0.15 * expected_counts


def test_dead_time_reduces_expected_rate_at_high_incidence():
    base = dict(
        sources=(RadiationSource(source_id="s", x=1.0, y=1.0, reference_cps_at_1m=2000.0),),
    )
    no_dead = make_scenario(detector=DetectorConfig(integration_time_s=1.0, background_cps=0.0), **base)
    with_dead = make_scenario(
        detector=DetectorConfig(integration_time_s=1.0, background_cps=0.0, dead_time_s=0.001),
        **base,
    )
    field_no = GammaField(no_dead)
    field_dead = GammaField(with_dead)
    pose = Pose2D(x=1.1, y=1.1)  # close: high incidence
    rate_no = field_no.expected_detector_cps(pose)
    rate_dead = field_dead.expected_detector_cps(pose)
    assert rate_dead < rate_no
    # Paralyzable dead-time model: rate_out = rate_in / (1 + rate_in * tau).
    expected_dead = rate_no / (1.0 + rate_no * with_dead.detector.dead_time_s)
    assert abs(rate_dead - expected_dead) < 1e-9


def test_saturation_caps_expected_rate():
    scenario = make_scenario(
        sources=(RadiationSource(source_id="s", x=1.0, y=1.0, reference_cps_at_1m=5000.0),),
        detector=DetectorConfig(integration_time_s=1.0, background_cps=0.0, max_cps=50.0),
    )
    field = GammaField(scenario)
    pose = Pose2D(x=1.1, y=1.1)
    assert field.expected_detector_cps(pose) == 50.0


def test_directional_response_faces_and_turns_away():
    scenario = make_scenario(
        sources=(RadiationSource(source_id="s", x=5.0, y=5.0, reference_cps_at_1m=100.0),),
        detector=DetectorConfig(
            integration_time_s=1.0, background_cps=0.0, directional_exponent=2.0
        ),
    )
    field = GammaField(scenario)
    pose = Pose2D(x=4.0, y=5.0, yaw=0.0)  # source is +x from pose: bearing = 0
    facing = field.source_rate_at(pose, 0)
    away = field.source_rate_at(Pose2D(x=4.0, y=5.0, yaw=np.pi), 0)
    assert facing > 0.0
    assert away == 0.0  # max(0, cos(pi))^2 = 0


def test_measurement_is_deterministic_for_fixed_seed():
    scenario = make_scenario()
    field = GammaField(scenario)
    pose = Pose2D(x=4.0, y=5.0)
    rng_a = np.random.default_rng(7)
    rng_b = np.random.default_rng(7)
    a = CountRateDetector(scenario.detector, field, rng_a)
    b = CountRateDetector(scenario.detector, field, rng_b)
    for _ in range(50):
        assert a.sample(pose) == b.sample(pose)
