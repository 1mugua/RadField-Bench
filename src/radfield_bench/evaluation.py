from __future__ import annotations

from math import hypot
from typing import Any

from .models import EpisodeState, Scenario


def evaluate_episode(
    scenario: Scenario,
    state: EpisodeState,
    history: list[dict[str, object]],
    estimate: dict[str, Any],
) -> dict[str, object]:
    source_estimates = list(estimate.get("source_estimates", []))
    localization_errors: list[float] = []
    for source in scenario.sources:
        if source_estimates:
            localization_errors.append(
                min(
                    hypot(source.x - float(item["x"]), source.y - float(item["y"]))
                    for item in source_estimates
                )
            )

    visited_cells = {
        (
            round(float(row["real_pose"]["x"]) * 2.0),
            round(float(row["real_pose"]["y"]) * 2.0),
        )
        for row in history
    }
    world_area = (scenario.world.x_max - scenario.world.x_min) * (
        scenario.world.y_max - scenario.world.y_min
    )
    approximate_coverage = min(1.0, len(visited_cells) * 0.25 / world_area)

    localization_success = _localization_success(
        scenario, source_estimates
    )
    within_budget = state.cumulative_exposure <= scenario.task.dose_budget
    benchmark_success = within_budget and (
        state.success
        or (scenario.task.task_type == "source_localization" and localization_success)
    )

    return {
        "schema_version": "0.1",
        "scenario_id": scenario.scenario_id,
        "split": scenario.split,
        "task_type": scenario.task.task_type,
        "success": benchmark_success,
        "termination": {
            "terminated": state.terminated,
            "truncated": state.truncated,
            "failure_reason": state.failure_reason,
        },
        "mission": {
            "steps": state.step,
            "time_s": state.time_s,
            "collision_count": state.collision_count,
            "approximate_coverage_fraction": approximate_coverage,
        },
        "exposure": {
            "cumulative_count_equivalent": state.cumulative_exposure,
            "budget": scenario.task.dose_budget,
            "budget_fraction": state.cumulative_exposure / scenario.task.dose_budget,
            "within_budget": within_budget,
            "peak_measured_cps": state.peak_count_rate_cps,
        },
        "localization": {
            "reported_source_count": len(source_estimates),
            "true_source_count": len(scenario.sources),
            "nearest_error_m_per_true_source": localization_errors,
            "mean_error_m": (
                sum(localization_errors) / len(localization_errors)
                if localization_errors
                else None
            ),
            "tolerance_m": scenario.task.localization_tolerance_m,
            "success": localization_success,
        },
        "disclaimer": (
            "Exposure is a benchmark count-equivalent cost, not a certified dosimetric quantity."
        ),
    }


def _localization_success(scenario: Scenario, source_estimates: list[dict[str, Any]]) -> bool:
    """Greedily match distinct reported sources to true sources."""

    if len(source_estimates) < len(scenario.sources):
        return False
    unmatched = set(range(len(source_estimates)))
    for source in scenario.sources:
        candidates = [
            (
                hypot(source.x - float(source_estimates[index]["x"]), source.y - float(source_estimates[index]["y"])),
                index,
            )
            for index in unmatched
        ]
        if not candidates:
            return False
        distance, index = min(candidates)
        if distance > scenario.task.localization_tolerance_m:
            return False
        unmatched.remove(index)
    return True
