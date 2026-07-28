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


def test_blueprint_rejects_alias_collision_between_terms() -> None:
    data = load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    data["terminology"][1]["aliases"].append("while")
    with pytest.raises(ValidationError, match="同时属于"):
        CourseBlueprint.model_validate(data)


def test_blueprint_requires_formal_content_for_every_required_scope_term() -> None:
    data = load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    data["knowledge_scope"]["required"].append("for")
    with pytest.raises(ValidationError, match="没有正式教学内容"):
        CourseBlueprint.model_validate(data)


def test_blueprint_rejects_promoted_mentioned_only_term() -> None:
    data = load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    data["knowledge_scope"]["mentioned_only"].append("列表")
    data["knowledge_points"][0]["definition"] += " 正式讲解列表。"
    with pytest.raises(ValidationError, match="被提升为正式教学内容"):
        CourseBlueprint.model_validate(data)


@pytest.mark.parametrize(
    ("delivery_mode", "display_on_slide"),
    [
        ("teacher_optional", True),
        ("student_assignment", False),
        ("extension_challenge", False),
    ],
)
def test_blueprint_rejects_invalid_exercise_delivery_matrix(
    delivery_mode: str,
    display_on_slide: bool,
) -> None:
    data = load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    data["exercises"][0]["delivery_mode"] = delivery_mode
    data["exercises"][0]["display_on_slide"] = display_on_slide
    with pytest.raises(ValidationError):
        CourseBlueprint.model_validate(data)
