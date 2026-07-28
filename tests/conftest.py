"""Shared fixed data for offline tests."""

from __future__ import annotations

import pytest

from models.blueprint import CourseBlueprint
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck
from utils.file_manager import load_demo_package


@pytest.fixture()
def demo_models() -> tuple[CourseBlueprint, LessonPlan, SlideDeck]:
    package = load_demo_package()
    return (
        CourseBlueprint.model_validate(package["blueprint"]),
        LessonPlan.model_validate(package["lesson_plan"]),
        SlideDeck.model_validate(package["slide_deck"]),
    )
