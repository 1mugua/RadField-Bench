# Action schema v0.1

The action is the only control the agent sends. Its JSON form is:

```json
{
  "linear_velocity_mps": 0.4,
  "angular_velocity_rps": 0.2
}
```

## Semantics

- `linear_velocity_mps`: commanded linear velocity of a differential-drive
  robot, in m/s. Negative values are allowed (reverse driving).
- `angular_velocity_rps`: commanded angular velocity in rad/s, positive
  counter-clockwise.

## Fixed rules (v0.1)

1. **Clipping.** The environment clips each command to the scenario limits:
   `|linear| <= robot.max_linear_velocity_mps`,
   `|angular| <= robot.max_angular_velocity_rps`. Clipping is silent and
   deterministic; the agent never receives an error for out-of-range commands.
2. **Fixed timestep.** Every accepted action advances the environment by exactly
   `time_step_s`. There is no variable-duration control in v0.1.
3. **Kinematics.** The robot integrates as
   `yaw += angular * dt; x += linear * cos(yaw) * dt; y += linear * sin(yaw) * dt`.
4. **Collision.** If the candidate pose after one step lies outside the world or
   inside an obstacle, the robot does not move, the step still counts, and
   `collision_count` increments. The agent observes the unchanged pose and the
   collision flag in `info`.
5. **Episode end.** Calling `step()` after the episode has terminated or
   truncated raises `RuntimeError` with a message directing the caller to
   `reset()`. Agents must detect terminal flags and stop stepping.

## Example episode rules

```text
step() before reset():        allowed (implicit start at scenario start)
step() after termination:     RuntimeError
action outside limits:        clipped, no error
collision on a step:          position unchanged, step advances, collision += 1
```

## Versioning

Changing the control space, clipping rule, timestep semantics, or collision
behavior is a breaking change that bumps `schema_version`. v0.1 is frozen once
the M1.5 milestone gate passes.
