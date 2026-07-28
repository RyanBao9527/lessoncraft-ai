"""Reusable deterministic validation helpers."""

from __future__ import annotations

from models.blueprint import CourseBlueprint


def duration_delta(blueprint: CourseBlueprint) -> int:
    """Return scheduled minutes minus requested course minutes."""

    scheduled = sum(step.duration_minutes for step in blueprint.lesson_flow)
    return scheduled - blueprint.course.duration_minutes


def duration_is_reasonable(blueprint: CourseBlueprint, tolerance: float = 0.1) -> bool:
    """Accept a schedule within 10% of the requested duration by default."""

    allowed = max(5, round(blueprint.course.duration_minutes * tolerance))
    return abs(duration_delta(blueprint)) <= allowed


def objective_coverage(blueprint: CourseBlueprint) -> dict[str, dict[str, bool]]:
    """Map each objective to required step/activity-or-exercise coverage."""

    coverage: dict[str, dict[str, bool]] = {}
    for objective in blueprint.learning_objectives:
        objective_id = objective.id
        coverage[objective_id] = {
            "step": any(objective_id in item.objective_ids for item in blueprint.lesson_flow),
            "activity_or_exercise": any(
                objective_id in item.objective_ids
                for item in [*blueprint.activities, *blueprint.exercises]
            ),
        }
    return coverage
