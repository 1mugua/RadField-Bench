from pathlib import Path

from radfield_bench.environment import RadFieldEnv
from radfield_bench.models import Action
from radfield_bench.scenario import load_scenario


ROOT = Path(__file__).parents[1]


def test_reset_with_same_seed_replays_counts():
    scenario = load_scenario(ROOT / "scenarios/train/open_room_single_source.yaml")
    env = RadFieldEnv(scenario)
    first = env.reset(seed=123)
    first_next, *_ = env.step(Action(0.2, 0.1))
    second = env.reset(seed=123)
    second_next, *_ = env.step(Action(0.2, 0.1))
    assert first.counts == second.counts
    assert first_next.counts == second_next.counts

