# Observation schema v0.1

The observation is the only input an agent receives per step. Both `reset()` and
`step()` return the same contract. Its JSON form is:

```json
{
  "schema_version": "0.1",
  "step": 12,
  "time_s": 3.0,
  "pose_estimate": {"x": 2.1, "y": 1.8, "yaw": 0.42},
  "pose_covariance": [0.0004, 0.0004, 0.0004],
  "counts": 18,
  "count_rate_cps": 37.0,
  "integration_time_s": 0.5,
  "cumulative_exposure": 112.0,
  "remaining_exposure_budget": 618.2
}
```

## Fields

| Field | Type | Unit | Visible to agent | Notes |
|---|---|---|---|---|
| `schema_version` | string | — | yes | observation contract version, currently `"0.1"` |
| `step` | int | — | yes | zero-based environment step |
| `time_s` | float | s | yes | simulation clock, starts at 0 on `reset()` |
| `pose_estimate` | `{x, y, yaw}` | m, m, rad | yes | **estimated** pose from odometry; equals true pose only in `oracle_pose` mode |
| `pose_covariance` | `[var_x, var_y, var_yaw]` | m^2, m^2, rad^2 | yes | estimate uncertainty; all zeros in `oracle_pose` mode |
| `counts` | int | counts | yes | raw detector counts over the integration window |
| `count_rate_cps` | float | counts/s | yes | measured rate `counts / integration_time_s` |
| `integration_time_s` | float | s | yes | detector integration window length |
| `cumulative_exposure` | float | count-equiv | yes | benchmark exposure accumulated so far |
| `remaining_exposure_budget` | float | count-equiv | yes | `max(0, dose_budget - cumulative_exposure)` |

## Coordinate system and timing

- The world is a 2D axis-aligned plane; `x`/`y` are world coordinates, `yaw` is
  the heading in radians, zero along +x, positive counter-clockwise.
- `time_s` advances by exactly `time_step_s` per step; sensor time equals
  environment time (no transport delay in v0.1).
- `counts` is sampled over the most recent `integration_time_s` window ending at
  the current pose.

## Visibility rule

An agent must be able to produce its full policy from the observation alone.
The following are **evaluator-only** and must never appear in an observation:

```text
true robot pose (when pose_mode is noisy_odometry)
source positions
source strengths
true radiation field values
material attenuation map
expected (noiseless) detector rate
hidden scenario labels
```

## Pose modes

- `oracle_pose`: `pose_estimate` equals the true pose, covariance is zero. For
  debugging and upper-bound runs only.
- `noisy_odometry`: `pose_estimate` is produced by a noisy odometry model with
  per-step translation/rotation noise and accumulated drift; `pose_covariance`
  is non-zero. Formal benchmark results must use this mode.

## Versioning

Changing a field name, unit, visibility, or adding a required field is a
breaking change that bumps `schema_version` and creates a new observation
contract. v0.1 is frozen once the M1.5 milestone gate passes.
