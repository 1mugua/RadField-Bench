# Result schema v0.1

Every completed run writes four artifacts:

```text
manifest.json       immutable scenario and software identity
trajectory.csv      time-ordered agent-visible measurements and pose
estimate.json       agent-reported estimates only
metrics.json        evaluator output
```

The evaluator may use hidden ground truth. A submitted agent must never need
to read `sources` or a ground-truth field map while producing `estimate.json`.

Minimum metric groups:

- `mission`: steps, time, collisions, coverage;
- `exposure`: cumulative benchmark exposure, budget, peak count rate;
- `localization`: reported/true source counts, matching errors and tolerance;
- `termination`: success, truncation and failure reason.

The current exposure value is a **count-equivalent benchmark cost**. It is not a
calibrated dose quantity and must not be used for radiation protection decisions.

