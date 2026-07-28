"""Core consistency rules."""

from __future__ import annotations

from models.blueprint import CourseBlueprint
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck
from services.consistency_checker import ConsistencyChecker
from services.course_generator import normalize_slide_deck_sources
from services.revision_service import RevisionService


def _check_by_name(report: object, name: str) -> object:
    return next(item for item in report.checks if item.name == name)


def test_demo_package_passes_all_checks(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    report = ConsistencyChecker().check(*demo_models)
    assert report.status == "pass"
    assert all(item.status == "pass" for item in report.checks)


def test_objective_coverage_detects_missing_slide(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = deck.model_copy(deep=True)
    for slide in broken.slides:
        slide.objective_ids = [
            item for item in slide.objective_ids if item != "OBJ-02"
        ]
    report = ConsistencyChecker().check(blueprint, lesson_plan, broken)
    check = _check_by_name(report, "objective_coverage")
    assert check.status == "fail"
    assert any("OBJ-02" in issue for issue in check.issues)


def test_unknown_ppt_knowledge_is_blocking(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = deck.model_copy(deep=True)
    broken.slides[2].knowledge_ids.append("K-99")
    report = ConsistencyChecker().check(blueprint, lesson_plan, broken)
    check = _check_by_name(report, "unknown_slide_knowledge")
    assert check.status == "fail"
    assert "K-99" in check.issues[0]


def test_lesson_and_slides_must_share_code_references(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken_plan = lesson_plan.model_copy(deep=True)
    broken_plan.code_example_ids = broken_plan.code_example_ids[:-1]
    report = ConsistencyChecker().check(blueprint, broken_plan, deck)
    check = _check_by_name(report, "code_example_consistency")
    assert check.status == "fail"
    assert any("不一致" in issue for issue in check.issues)


def test_demo_revision_rescales_duration_and_rechecks(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, _, _ = demo_models
    package = RevisionService().revise_package(blueprint, "请改成 60 分钟")
    updated = CourseBlueprint.model_validate(package["blueprint"])
    assert updated.course.duration_minutes == 60
    assert sum(step.duration_minutes for step in updated.lesson_flow) == 60
    assert package["consistency_report"]["status"] == "pass"


def test_excluded_else_is_detected_as_formal_teaching(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = blueprint.model_copy(deep=True)
    broken.knowledge_points[-1].definition += " 也正式讲解 else。"
    report = ConsistencyChecker().check(broken, lesson_plan, deck)
    check = _check_by_name(report, "knowledge_scope")
    assert check.status == "fail"
    assert any("else" in issue for issue in check.issues)


def test_presentation_minutes_must_fit_step_budget(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = deck.model_copy(deep=True)
    slide = next(item for item in broken.slides if item.id == "SLIDE-13")
    slide.speaker_notes.suggested_minutes = 10
    report = ConsistencyChecker().check(blueprint, lesson_plan, broken)
    check = _check_by_name(report, "presentation_time_budget")
    assert check.status == "warning"
    assert any("STEP-05" in issue for issue in check.issues)


def test_illegal_slide_objective_is_repaired_and_reported(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = deck.model_copy(deep=True)
    slide = next(item for item in broken.slides if item.id == "SLIDE-03")
    slide.objective_ids.append("OBJ-02")
    normalized = normalize_slide_deck_sources(blueprint, broken)
    repaired = next(item for item in normalized.slides if item.id == "SLIDE-03")
    assert repaired.objective_ids == ["OBJ-01"]
    report = ConsistencyChecker().check(blueprint, lesson_plan, normalized)
    check = _check_by_name(report, "slide_objective_subset")
    assert check.status == "warning"
    assert any("已自动移除" in issue for issue in check.issues)
