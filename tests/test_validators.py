"""Deterministic validation helper tests."""

from __future__ import annotations

from models.blueprint import CourseBlueprint
from utils.validators import duration_delta, duration_is_reasonable


def test_lesson_flow_duration_matches_course(
    demo_models: tuple[CourseBlueprint, object, object],
) -> None:
    blueprint = demo_models[0]
    assert duration_delta(blueprint) == 0
    assert duration_is_reasonable(blueprint)


def test_duration_check_detects_large_gap(
    demo_models: tuple[CourseBlueprint, object, object],
) -> None:
    blueprint = demo_models[0].model_copy(deep=True)
    blueprint.lesson_flow[-1].duration_minutes += 20
    assert duration_delta(blueprint) == 20
    assert not duration_is_reasonable(blueprint)
