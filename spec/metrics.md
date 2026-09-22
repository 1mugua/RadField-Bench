# Metrics v0.1

Metrics are the evaluator's output. They are computed from the scenario, the
environment state, the agent-visible history, and the agent's estimate. An
agent never computes its own metrics.

## Three rate levels (must not be conflated)

| Level | Name | Where it comes from | Noise | Detector model |
|---|---|---|---|---|
| 1 | **true field rate** | `GammaField.expected_source_cps(pose)` — ideal point-source sum with attenuation | none | none |
| 2 | **expected detector rate** | `GammaField.expected_detector_cps(pose)` — after efficiency, background, dead time, saturation | none | yes |
| 3 | **measured count rate** | `counts / integration_time_s` from a Poisson sample of level 2 | Poisson sampling | yes |

Level 1 and 2 are evaluator-only in formal runs. Level 3 is what the agent
observes. Reports must never call level 3 a "dose rate"; the exposure value is a
**count-equivalent benchmark cost**, not a calibrated dosimetric quantity.

## Termination priority

States are exclusive and evaluated in this order per step:

1. `dose_budget_exceeded` → `terminated=True`, `success=False`,
   `failure_reason="dose_budget_exceeded"`.
2. goal reached (if `task.goal` is set) → `terminated=True`, `success=True`,
   only if the budget was not exceeded.
3. `step >= task.max_steps` → `truncated=True`,
   `failure_reason="max_steps"`, only if not already terminated.

## Hard budget rule

> Exceeding the exposure budget fails the mission even if the source is located
> perfectly.

`within_budget = cumulative_exposure <= dose_budget`; if false,
`benchmark_success` is always false.

## Benchmark success

```text
benchmark_success = within_budget AND (
    state.success OR
    (task_type == "source_localization" AND localization_success)
)
```

`localization_success` greedily matches each reported source to a distinct true
source within `localization_tolerance_m`; it fails if fewer estimates than true
sources are reported. It is a *localization* result, not a *safe mission*
result; reports must keep the two separate.

## Metric groups (schema v0.1)

| Group | Fields |
|---|---|
| `termination` | `terminated`, `truncated`, `failure_reason` |
| `mission` | `steps`, `time_s`, `collision_count`, `approximate_coverage_fraction` |
| `exposure` | `cumulative_count_equivalent`, `budget`, `budget_fraction`, `within_budget`, `peak_measured_cps` |
| `localization` | `reported_source_count`, `true_source_count`, `nearest_error_m_per_true_source`, `mean_error_m`, `tolerance_m`, `success` |

`approximate_coverage_fraction` is a coarse grid-based estimate and is marked as
approximate in outputs.

## Run artifacts

Every completed run writes `manifest.json`, `trajectory.csv`, `estimate.json`,
and `metrics.json`. `trajectory.csv` contains only agent-visible fields; ground
truth used by the evaluator is never published in a run artifact.

## Versioning

Changes to metric definitions, success semantics, or artifact layout bump the
result schema version. The result schema is frozen at `0.1` when the M1.5 gate
passes.
