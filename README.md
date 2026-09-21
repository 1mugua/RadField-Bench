# RadField-Bench

RadField-Bench is an open benchmark for radiation-aware robot exploration,
mapping, and source localization under sensor uncertainty and exposure limits.

The current milestone is a simulator-independent Python reference core. It
provides a versioned scenario format, a real-time gamma field approximation,
a count-rate detector model, a closed-loop task environment, baseline agents,
and deterministic evaluation artifacts. The reference baselines currently
include random walk, lawnmower coverage, and a model-mismatched Bayesian grid
localizer. ROS 2 and Gazebo integration will be implemented against these
contracts rather than defining a second set of semantics.

## Scope of the first release

- 2D indoor UGV missions
- gamma point sources
- material shielding and inverse-square propagation
- Poisson detector counts, background, efficiency, dead time, and saturation
- field mapping, source localization, and dose-constrained exploration metrics
- public train/validation scenarios and reserved test identifiers

This software is a research benchmark. It is not certified radiation-protection
software and must not be used to make real-world safety decisions.

## Quick start

The repository runs with Python 3.10 or later.

```powershell
python -m pip install -e .
python -m radfield_bench validate scenarios/train/open_room_single_source.yaml
python -m radfield_bench run scenarios/train/open_room_single_source.yaml --baseline lawnmower --output runs/open-room
python -m radfield_bench run scenarios/train/open_room_single_source.yaml --baseline bayes-grid --output runs/open-room-bayes
python -m radfield_bench evaluate runs/open-room
python -m pytest
```

The run command writes `manifest.json`, `trajectory.csv`, `estimate.json`, and
`metrics.json`. Ground truth is used by the evaluator but is not passed to the
agent observation.

## Repository layout

```text
src/radfield_bench/  reference implementation
scenarios/           versioned benchmark scenarios
spec/                scenario and result contracts
tests/               physics, schema, and end-to-end tests
docs/                design and benchmark documentation
```

The reviewed project proposal is in
[`RADFIELD_BENCH_PROPOSAL.md`](RADFIELD_BENCH_PROPOSAL.md).
