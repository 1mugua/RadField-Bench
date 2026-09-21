# Implementation status

## Completed in the first implementation pass

- Python package and editable installation via `pyproject.toml`.
- Scenario schema v0.1 with validation for world bounds, obstacles, materials,
  sources, detector, robot, task, and split metadata.
- Real-time gamma approximation: inverse-square point sources, material
  attenuation through axis-aligned obstacles, detector efficiency, direction
  response, dead time, saturation, and Poisson count sampling.
- Closed-loop environment with clipped actions, collision checks, cumulative
  benchmark exposure, dose-budget termination, and hidden source truth.
- Baselines: random walk, lawnmower coverage, and a deliberately
  model-mismatched Bayesian grid localizer.
- JSON/CSV run artifacts and metrics evaluator.
- Three reference scenarios and nine automated tests.
- CI workflow for Python 3.10 and 3.12.

## Not implemented yet

- ROS 2/Gazebo bridge. The current machine does not expose `ros2` or `gz`, so
  this should be implemented in a Linux/ROS development environment after the
  Python contracts are reviewed.
- OpenMC/Geant4 calibration adapter. Neither Python package is installed in the
  current environment; no high-fidelity claim is made by the current model.
- True dose units, isotope spectra, neutron fields, alpha/beta contamination,
  and radiation-induced electronics degradation.
- Field-mapping uncertainty metrics and a multi-source Bayesian estimator.
- Hidden test service, leaderboard, container image, and real detector
  calibration data.

## Current safety/validity boundary

The exposure quantity is explicitly a count-equivalent benchmark cost. It is
not a calibrated dose rate and must not be used for operational radiation
protection decisions. The current implementation is suitable for software
contract tests and algorithm prototyping only.

## Next implementation gate

Before adding ROS 2/Gazebo, review and freeze:

1. whether `reference_cps_at_1m` is the right public source-strength unit;
2. whether task success must always require staying within the exposure budget;
3. the detector observation contract and whether pose should be noisy;
4. the first high-fidelity calibration geometry and material table;
5. the license and redistribution terms for every external dataset and asset.

