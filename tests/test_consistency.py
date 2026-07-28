"""Core consistency rules."""

from __future__ import annotations

from models.blueprint import CourseBlueprint
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck
from services.consistency_checker import ConsistencyChecker
from services.course_generator import (
    CourseGenerator,
    normalize_slide_deck_sources,
    sync_lesson_slide_ids,
)
from services.revision_service import RevisionService


def _check_by_name(report: object, name: str) -> object:
    return next(item for item in report.checks if item.name == name)


def test_demo_package_passes_all_checks(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    report = ConsistencyChecker().check(*demo_models)
    assert report.status == "pass"
    assert len(report.checks) == 22
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


def test_required_scope_without_formal_content_is_blocking(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = blueprint.model_copy(deep=True)
    broken.knowledge_scope.required.append("for")
    report = ConsistencyChecker().check(broken, lesson_plan, deck)
    check = _check_by_name(report, "knowledge_scope")
    assert check.status == "fail"
    assert any("for" in issue and "未出现" in issue for issue in check.issues)


def test_mentioned_only_cannot_be_promoted_to_formal_knowledge(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken = blueprint.model_copy(deep=True)
    broken.knowledge_scope.mentioned_only.append("列表")
    broken.knowledge_points[0].definition += " 正式讲解列表。"
    report = ConsistencyChecker().check(broken, lesson_plan, deck)
    check = _check_by_name(report, "knowledge_scope")
    assert check.status == "fail"
    assert any("仅提及知识点“列表”" in issue for issue in check.issues)


def test_terminology_alias_satisfies_consistency_check(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    alias_blueprint = blueprint.model_copy(deep=True)
    alias_blueprint.terminology[0].term = "条件循环语句"
    alias_blueprint.terminology[0].aliases = ["while"]
    report = ConsistencyChecker().check(alias_blueprint, lesson_plan, deck)
    check = _check_by_name(report, "terminology_consistency")
    assert check.status == "pass"
    assert report.status == "pass"


def test_exercise_delivery_is_normalized_before_final_check(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models
    broken_deck = deck.model_copy(deep=True)
    for slide in broken_deck.slides:
        slide.exercise_ids = [
            item for item in slide.exercise_ids if item != "EX-03"
        ]
        slide.content = [
            item
            for item in slide.content
            if "增加猜测次数统计" not in item
        ]
    broken_deck.slides[-1].exercise_ids.append("EX-02")
    broken_deck.slides[-1].content.insert(
        0,
        next(item.question for item in blueprint.exercises if item.id == "EX-02"),
    )
    broken_plan = lesson_plan.model_copy(deep=True)
    broken_plan.homework = [
        next(item.question for item in blueprint.exercises if item.id == "EX-02"),
        "把挑战题换一种说法",
    ]

    normalized_deck = normalize_slide_deck_sources(blueprint, broken_deck)
    normalized_plan = sync_lesson_slide_ids(
        broken_plan,
        normalized_deck,
        blueprint,
    )
    report = ConsistencyChecker().check(
        blueprint,
        normalized_plan,
        normalized_deck,
    )
    slide_refs = {
        exercise_id
        for slide in normalized_deck.slides
        for exercise_id in slide.exercise_ids
    }
    expected_homework = [
        item.question
        for item in blueprint.exercises
        if item.delivery_mode
        in {"student_assignment", "extension_challenge"}
    ]
    assert "EX-02" not in slide_refs
    assert not any(
        next(item.question for item in blueprint.exercises if item.id == "EX-02")
        in slide.content
        for slide in normalized_deck.slides
    )
    assert "EX-03" in slide_refs
    assert any(
        next(item.question for item in blueprint.exercises if item.id == "EX-03")
        in slide.content
        for slide in normalized_deck.slides
    )
    assert normalized_plan.homework == expected_homework
    assert len(report.checks) == 22
    assert report.status == "pass"


def test_real_generation_keeps_22_authoritative_checks(
    demo_models: tuple[CourseBlueprint, LessonPlan, SlideDeck],
) -> None:
    blueprint, lesson_plan, deck = demo_models

    class SemanticFalsePositiveClient:
        def generate_json(self, _system: str, _user: str) -> dict[str, object]:
            return {
                "status": "warning",
                "checks": [
                    {
                        "name": "terminology_consistency",
                        "status": "warning",
                        "scope": "execution",
                        "issues": ["忽略 aliases 后误认为标准词未出现"],
                    },
                    {
                        "name": "exercise_delivery",
                        "status": "warning",
                        "scope": "execution",
                        "issues": ["误把教师追加题当作学生作业"],
                    },
                ],
                "blocking_issues": [],
                "warnings": [
                    "忽略 aliases 后误认为标准词未出现",
                    "误把教师追加题当作学生作业",
                ],
            }

    generator = CourseGenerator(SemanticFalsePositiveClient())  # type: ignore[arg-type]
    report = generator.generate_consistency_report(
        blueprint,
        lesson_plan,
        deck,
    )
    assert len(report.checks) == 22
    assert report.status == "pass"
    assert all(item.status == "pass" for item in report.checks)


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
