"""Offline checks for classroom rhythm and concise navigation outputs."""

from __future__ import annotations

from models.blueprint import CourseBlueprint
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck
from services.consistency_checker import ConsistencyChecker
from services.course_generator import build_step_bindings, sync_lesson_slide_ids


def test_slide_layouts_and_types_are_varied(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    _, _, deck = demo_models
    assert len({slide.layout for slide in deck.slides}) >= 6
    assert len({slide.slide_type for slide in deck.slides}) >= 10


def test_every_four_content_slides_include_interaction(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    _, _, deck = demo_models
    slides = [slide for slide in deck.slides if slide.slide_type != "cover"]
    for start in range(len(slides) - 3):
        window = slides[start : start + 4]
        assert any(
            slide.interaction and slide.interaction.type != "none"
            for slide in window
        )


def test_student_facing_content_stays_bounded(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    _, _, deck = demo_models
    assert all(len(slide.content) <= 5 for slide in deck.slides)
    assert all(
        len(item) <= 120 for slide in deck.slides for item in slide.content
    )


def test_all_code_displays_reference_blueprint(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, _, deck = demo_models
    valid_ids = {item.id for item in blueprint.code_examples}
    references = {
        slide.code_display.code_example_id
        for slide in deck.slides
        if slide.code_display and slide.code_display.code_example_id
    }
    assert references
    assert references <= valid_ids


def test_concise_lesson_flow_has_complete_navigation(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    valid_slide_ids = {slide.id for slide in deck.slides}
    assert lesson_plan.plan_type == "concise"
    assert [stage.step_id for stage in lesson_plan.stages] == [
        step.id for step in blueprint.lesson_flow
    ]
    for stage in lesson_plan.stages:
        assert stage.slide_ids
        assert set(stage.slide_ids) <= valid_slide_ids
        assert len(stage.teacher_activity) <= 180
        assert len(stage.student_activity) <= 180
        assert len(stage.key_question) <= 120
        assert len(stage.assessment) <= 180


def test_lesson_plan_does_not_copy_full_speaker_notes(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    _, lesson_plan, deck = demo_models
    lesson_text = lesson_plan.model_dump_json()
    for slide in deck.slides:
        for note in (
            slide.speaker_notes.explanation,
            slide.speaker_notes.demo,
            slide.speaker_notes.transition,
        ):
            if len(note) >= 45:
                assert note not in lesson_text


def test_consistency_detects_missing_interaction_rhythm(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = deck.model_copy(deep=True)
    for slide in broken.slides:
        if slide.interaction:
            slide.interaction.type = "none"
            slide.interaction.prompt = ""
            slide.interaction.expected_response = ""
    report = ConsistencyChecker().check(blueprint, lesson_plan, broken)
    check = next(
        item for item in report.checks if item.name == "slide_interaction_rhythm"
    )
    assert check.status == "warning"


def test_step_duration_parts_and_course_total_are_exact(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, _ = demo_models
    assert sum(
        step.duration.total_minutes for step in blueprint.lesson_flow
    ) == blueprint.course.duration_minutes
    assert sum(
        stage.duration.total_minutes for stage in lesson_plan.stages
    ) == blueprint.course.duration_minutes
    for step in blueprint.lesson_flow:
        assert (
            step.duration.presentation_minutes
            + step.duration.student_practice_minutes
            + step.duration.transition_minutes
            == step.duration.total_minutes
            == step.duration_minutes
        )


def test_step03_uses_input_variations_without_modifying_answer(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    step = next(item for item in blueprint.lesson_flow if item.id == "STEP-03")
    stage = next(item for item in lesson_plan.stages if item.step_id == "STEP-03")
    assert step.student_action is not None
    assert step.student_action.forbidden_actions == ["修改answer变量"]
    assert stage.student_activity == "先预测运行结果，再使用不同输入运行同一份代码进行验证。"
    operational_text = stage.student_activity + "".join(
        slide.speaker_notes.demo
        for slide in deck.slides
        if "STEP-03" in slide.source_step_ids
    )
    assert "修改answer变量" not in operational_text.replace(" ", "")


def test_code_prediction_activity_is_bound_to_actual_code_pages(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, _, deck = demo_models
    binding = next(item for item in deck.step_bindings if item.step_id == "STEP-03")
    assert binding.slide_ids == ["SLIDE-08", "SLIDE-09"]
    assert binding.activity_ids == ["ACT-03"]
    assert binding.code_example_ids == ["CODE-01"]
    for slide_id in binding.slide_ids:
        slide = next(item for item in deck.slides if item.id == slide_id)
        assert slide.code_example_id == "CODE-01"
        assert "ACT-03" in slide.activity_ids


def test_every_slide_objective_is_from_its_source_steps(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, _, deck = demo_models
    steps = {item.id: item for item in blueprint.lesson_flow}
    for slide in deck.slides:
        if not slide.source_step_ids:
            continue
        allowed = {
            objective_id
            for step_id in slide.source_step_ids
            for objective_id in steps[step_id].objective_ids
        }
        assert set(slide.objective_ids) <= allowed


def test_exercise_delivery_is_explicit_and_consistent(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    exercises = {item.id: item for item in blueprint.exercises}
    slide_refs = {
        exercise_id for slide in deck.slides for exercise_id in slide.exercise_ids
    }
    assert exercises["EX-02"].delivery_mode == "teacher_optional"
    assert exercises["EX-02"].display_on_slide is False
    assert "EX-02" not in slide_refs
    assert exercises["EX-02"].question not in lesson_plan.homework
    assert exercises["EX-03"].delivery_mode == "extension_challenge"
    assert exercises["EX-03"].display_on_slide is True
    assert "EX-03" in slide_refs
    assert exercises["EX-03"].question in lesson_plan.homework


def test_lesson_page_mapping_is_derived_from_slide_deck(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    expected_bindings = build_step_bindings(blueprint, deck)
    assert deck.step_bindings == expected_bindings
    blank = lesson_plan.model_copy(deep=True)
    for stage in blank.stages:
        stage.slide_ids = []
    synced = sync_lesson_slide_ids(blank, deck, blueprint)
    binding_map = {item.step_id: item for item in deck.step_bindings}
    for stage in synced.stages:
        assert stage.slide_ids == binding_map[stage.step_id].slide_ids
