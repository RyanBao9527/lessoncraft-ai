"""Model validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.blueprint import CourseBlueprint
from models.course_input import CourseInput
from utils.file_manager import load_json, PROJECT_ROOT


def test_course_input_rejects_too_short_duration() -> None:
    with pytest.raises(ValidationError):
        CourseInput(
            language="Python",
            topic="循环",
            age_range="10～12 岁",
            student_level="学过变量",
            duration_minutes=15,
            core_goal="理解并使用 while 循环",
            teaching_style="互动实践型",
            max_slides=12,
        )


def test_course_input_accepts_default_demo() -> None:
    model = CourseInput.model_validate(
        load_json(PROJECT_ROOT / "examples" / "sample_input.json")
    )
    assert model.language == "Python"
    assert model.max_slides == 15


def test_blueprint_rejects_invalid_id_format() -> None:
    data = load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    data["learning_objectives"][0]["id"] = "OBJECTIVE-1"
    with pytest.raises(ValidationError):
        CourseBlueprint.model_validate(data)


def test_blueprint_rejects_unknown_cross_reference() -> None:
    data = load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    data["knowledge_points"][0]["objective_ids"] = ["OBJ-99"]
    with pytest.raises(ValidationError):
        CourseBlueprint.model_validate(data)


def test_blueprint_rejects_invalid_step_duration_breakdown() -> None:
    data = load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    data["lesson_flow"][0]["duration"]["student_practice_minutes"] += 1
    with pytest.raises(ValidationError):
        CourseBlueprint.model_validate(data)
