# Scenario schema v0.1

The canonical machine-readable scenario is YAML. A scenario is immutable once
published under a benchmark version; changes create a new `scenario_id`.

Required top-level keys:

```yaml
schema_version: "0.1"
scenario_id: string
split: train | validation | test-iid | test-ood | test-sim2real
seed: integer
time_step_s: positive number
world: {bounds: ..., obstacles: [...]}
materials: {name: {linear_attenuation_per_m: non-negative number}}
sources: [{id, x, y, reference_cps_at_1m, isotope}]
detector: {integration_time_s, background_cps, efficiency, ...}
robot: {start, max_linear_velocity_mps, max_angular_velocity_rps}
task: {type, max_steps, dose_budget, ...}
```

The ground-truth source list and field values are not part of an agent's
observation. They are available to the evaluator for public development runs
and hidden evaluation infrastructure for held-out tests.

