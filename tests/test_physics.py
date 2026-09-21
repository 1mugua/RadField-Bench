from pathlib import Path

from radfield_bench.environment import RadFieldEnv
from radfield_bench.models import Pose2D
from radfield_bench.physics import GammaField
from radfield_bench.scenario import load_scenario


ROOT = Path(__file__).parents[1]


def test_inverse_square_decreases_with_distance():
    scenario = load_scenario(ROOT / "scenarios/train/open_room_single_source.yaml")
    field = GammaField(scenario)
    source = scenario.sources[0]
    near = field.source_rate_at(Pose2D(source.x - 1.0, source.y), 0)
    far = field.source_rate_at(Pose2D(source.x - 2.0, source.y), 0)
    assert near > far
    assert 3.5 < near / far < 4.5


def test_shielding_reduces_rate():
    scenario = load_scenario(ROOT / "scenarios/train/shielded_two_source.yaml")
    field = GammaField(scenario)
    source = scenario.sources[0]
    blocked = field.source_rate_at(Pose2D(5.0, 3.0), 0)
    unblocked = field.source_rate_at(Pose2D(2.8, source.y, 3.14159), 0)
    assert blocked < unblocked


def test_environment_observation_hides_truth():
    scenario = load_scenario(ROOT / "scenarios/train/open_room_single_source.yaml")
    env = RadFieldEnv(scenario)
    observation = env.reset()
    assert not hasattr(observation, "sources")
    assert observation.counts >= 0
