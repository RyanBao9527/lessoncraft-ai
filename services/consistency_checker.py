"""Deterministic traceability and consistency checks."""

from __future__ import annotations

import re

from models.blueprint import CourseBlueprint
from models.consistency import CheckResult, ConsistencyReport, ConsistencySummary
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck
from utils.validators import duration_delta, objective_coverage


class ConsistencyChecker:
    """Check IDs, coverage, order, duration, terms, and code traceability."""

    def check(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> ConsistencyReport:
        """Return a structured report without changing any course content."""

        checks = [
            self._objective_coverage(blueprint, slide_deck),
            self._knowledge_coverage(blueprint, lesson_plan, slide_deck),
            self._knowledge_scope(blueprint, lesson_plan, slide_deck),
            self._order(blueprint, lesson_plan, slide_deck),
            self._duration(blueprint, lesson_plan),
            self._duration_breakdown(blueprint, lesson_plan),
            self._presentation_budget(blueprint, slide_deck),
            self._terminology(blueprint, lesson_plan, slide_deck),
            self._code(blueprint, lesson_plan, slide_deck),
            self._lesson_slide_mapping(blueprint, lesson_plan, slide_deck),
            self._activity_slide_bindings(blueprint, slide_deck),
            self._slide_objective_subset(blueprint, slide_deck),
            self._student_actions(blueprint, lesson_plan, slide_deck),
            self._exercise_mapping(blueprint),
            self._exercise_delivery(blueprint, lesson_plan, slide_deck),
            self._unknown_slide_knowledge(blueprint, slide_deck),
            self._unknown_lesson_content(blueprint, lesson_plan),
            self._interaction_rhythm(slide_deck),
            self._text_only_run(slide_deck),
            self._information_load(slide_deck),
            self._lesson_conciseness(lesson_plan, slide_deck),
            self._speaker_notes_conciseness(slide_deck),
        ]
        blocking = [issue for check in checks if check.status == "fail" for issue in check.issues]
        warnings = [
            issue for check in checks if check.status == "warning" for issue in check.issues
        ]
        status = "fail" if blocking else ("warning" if warnings else "pass")
        core_checks = [item for item in checks if item.scope == "core"]
        execution_checks = [item for item in checks if item.scope == "execution"]

        def scope_status(items: list[CheckResult]) -> str:
            if any(item.status == "fail" for item in items):
                return "fail"
            if any(item.status == "warning" for item in items):
                return "warning"
            return "pass"

        return ConsistencyReport(
            status=status,
            checks=checks,
            blocking_issues=blocking,
            warnings=warnings,
            summary=ConsistencySummary(
                core_fact_status=scope_status(core_checks),
                execution_alignment_status=scope_status(execution_checks),
                passed_checks=sum(item.status == "pass" for item in checks),
                warning_checks=sum(item.status == "warning" for item in checks),
                failed_checks=sum(item.status == "fail" for item in checks),
            ),
        )

    @staticmethod
    def _result(
        name: str,
        issues: list[str],
        severe: bool = True,
        scope: str = "core",
    ) -> CheckResult:
        return CheckResult(
            name=name,
            status=("fail" if severe else "warning") if issues else "pass",
            scope=scope,
            issues=issues,
        )

    def _objective_coverage(
        self, blueprint: CourseBlueprint, slide_deck: SlideDeck
    ) -> CheckResult:
        base = objective_coverage(blueprint)
        issues: list[str] = []
        for objective_id, coverage in base.items():
            if not coverage["step"]:
                issues.append(f"{objective_id} 没有对应教学环节")
            if not coverage["activity_or_exercise"]:
                issues.append(f"{objective_id} 没有对应课堂活动或练习")
            if not any(objective_id in slide.objective_ids for slide in slide_deck.slides):
                issues.append(f"{objective_id} 没有对应 PPT 页面")
        return self._result("objective_coverage", issues)

    def _knowledge_coverage(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        lesson_refs = {ref for stage in lesson_plan.stages for ref in stage.knowledge_ids}
        slide_refs = {ref for slide in slide_deck.slides for ref in slide.knowledge_ids}
        issues = []
        for item in blueprint.knowledge_points:
            if item.id not in lesson_refs:
                issues.append(f"{item.id} 未被教案覆盖")
            if item.id not in slide_refs:
                issues.append(f"{item.id} 未被 PPT 覆盖")
        return self._result("knowledge_coverage", issues)

    def _knowledge_scope(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        """Reject formal teaching of concepts explicitly excluded by Blueprint."""

        scope = blueprint.knowledge_scope
        corpus = "\n".join(
            [
                *(item.definition for item in blueprint.knowledge_points),
                *(item.teacher_activity for item in blueprint.lesson_flow),
                *(item.student_activity for item in blueprint.lesson_flow),
                *(item.code for item in blueprint.code_examples),
                *lesson_plan.key_points,
                *lesson_plan.difficult_points,
                *(
                    f"{stage.teacher_activity}\n{stage.student_activity}\n"
                    f"{stage.key_question}\n{stage.assessment}"
                    for stage in lesson_plan.stages
                ),
                *(
                    "\n".join(
                        [
                            slide.title,
                            *slide.content,
                            slide.interaction.prompt,
                            slide.speaker_notes.explanation,
                            slide.speaker_notes.question,
                            slide.speaker_notes.demo,
                            slide.speaker_notes.warning,
                            slide.speaker_notes.transition,
                        ]
                    )
                    for slide in slide_deck.slides
                ),
            ]
        )
        issues: list[str] = []
        for term in scope.excluded:
            pattern = rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])"
            if re.search(pattern, corpus, flags=re.IGNORECASE):
                issues.append(f"排除知识点“{term}”被作为正式教学内容使用")
        for term in scope.required:
            pattern = rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])"
            if not re.search(pattern, corpus, flags=re.IGNORECASE):
                issues.append(f"必教知识点“{term}”未出现在教学包")
        return self._result("knowledge_scope", issues)

    def _order(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        expected = [item.id for item in blueprint.lesson_flow]
        lesson_order = [item.step_id for item in lesson_plan.stages]
        issues = []
        if lesson_order != expected:
            issues.append(f"教案环节顺序 {lesson_order} 与 Blueprint {expected} 不一致")
        slide_order: list[str] = []
        for slide in slide_deck.slides:
            for step_id in slide.source_step_ids:
                if step_id not in slide_order:
                    slide_order.append(step_id)
        positions = [expected.index(item) for item in slide_order if item in expected]
        if positions != sorted(positions):
            issues.append(f"PPT 来源环节顺序 {slide_order} 未遵守 lesson_flow")
        return self._result("teaching_order", issues)

    def _duration(
        self, blueprint: CourseBlueprint, lesson_plan: LessonPlan
    ) -> CheckResult:
        issues = []
        if duration_delta(blueprint) != 0:
            issues.append(
                f"Blueprint 环节时间与课程时长相差 {duration_delta(blueprint)} 分钟"
            )
        plan_total = sum(item.duration_minutes for item in lesson_plan.stages)
        if plan_total != blueprint.course.duration_minutes:
            issues.append(
                f"教案课堂流程合计 {plan_total} 分钟，"
                f"课程要求 {blueprint.course.duration_minutes} 分钟"
            )
        return self._result("duration_total", issues)

    def _duration_breakdown(
        self, blueprint: CourseBlueprint, lesson_plan: LessonPlan
    ) -> CheckResult:
        """Require each structured duration to reconcile with its total."""

        issues: list[str] = []
        plan_steps = {item.step_id: item for item in lesson_plan.stages}
        for step in blueprint.lesson_flow:
            duration = step.duration
            parts = (
                duration.presentation_minutes
                + duration.student_practice_minutes
                + duration.transition_minutes
            )
            if parts != duration.total_minutes:
                issues.append(f"{step.id} 子时间合计 {parts} 分钟，不等于总时间")
            if duration.total_minutes != step.duration_minutes:
                issues.append(f"{step.id} 新旧时长字段不一致")
            plan_stage = plan_steps.get(step.id)
            if not plan_stage:
                continue
            if plan_stage.duration != duration:
                issues.append(f"{step.id} 教案没有逐项继承 Blueprint 时间拆分")
        return self._result("step_duration_breakdown", issues)

    def _presentation_budget(
        self, blueprint: CourseBlueprint, slide_deck: SlideDeck
    ) -> CheckResult:
        """Keep projected per-slide explanation time within each step budget."""

        issues: list[str] = []
        for step in blueprint.lesson_flow:
            slide_minutes = sum(
                slide.speaker_notes.suggested_minutes
                for slide in slide_deck.slides
                if step.id in slide.source_step_ids
            )
            budget = step.duration.presentation_minutes
            if slide_minutes > budget:
                issues.append(
                    f"{step.id} PPT 备注时间 {slide_minutes} 分钟，"
                    f"超过投屏讲解预算 {budget} 分钟"
                )
        return self._result(
            "presentation_time_budget",
            issues,
            severe=False,
            scope="execution",
        )

    def _terminology(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        package_text = (
            lesson_plan.model_dump_json()
            + slide_deck.model_dump_json()
        )
        issues = [
            f"术语“{item.term}”未出现在教案或 PPT 中"
            for item in blueprint.terminology
            if item.term not in package_text
        ]
        return self._result(
            "terminology_consistency",
            issues,
            severe=False,
            scope="execution",
        )

    def _code(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        valid = {item.id for item in blueprint.code_examples}
        lesson_refs = set(lesson_plan.code_example_ids)
        slide_refs = {
            slide.code_example_id for slide in slide_deck.slides if slide.code_example_id
        }
        slide_refs.update(
            slide.code_display.code_example_id
            for slide in slide_deck.slides
            if slide.code_display and slide.code_display.code_example_id
        )
        issues = []
        if lesson_refs - valid:
            issues.append(f"教案引用不存在的代码: {sorted(lesson_refs - valid)}")
        if slide_refs - valid:
            issues.append(f"PPT 引用不存在的代码: {sorted(slide_refs - valid)}")
        if lesson_refs != slide_refs:
            issues.append(
                f"教案代码引用 {sorted(lesson_refs)} 与 PPT {sorted(slide_refs)} 不一致"
            )
        for slide in slide_deck.slides:
            if slide.layout == "code" and not slide.code_example_id:
                issues.append(f"{slide.id} 是代码页但没有 code_example_id")
        return self._result("code_example_consistency", issues)

    def _lesson_slide_mapping(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        slide_ids = {item.id for item in slide_deck.slides}
        slide_steps = {
            ref for slide in slide_deck.slides for ref in slide.source_step_ids
        }
        issues = []
        for stage in lesson_plan.stages:
            if stage.step_id not in slide_steps:
                issues.append(f"{stage.step_id} 没有来源对应的 PPT 页面")
            unknown_slides = set(stage.slide_ids) - slide_ids
            if unknown_slides:
                issues.append(f"{stage.step_id} 引用了不存在的页面 {sorted(unknown_slides)}")
            expected_slides = {
                slide.id
                for slide in slide_deck.slides
                if stage.step_id in slide.source_step_ids
            }
            if set(stage.slide_ids) != expected_slides:
                issues.append(
                    f"{stage.step_id} 的 PPT 页码未与实际来源页同步"
                )
        return self._result(
            "lesson_slide_mapping",
            issues,
            severe=False,
            scope="execution",
        )

    def _activity_slide_bindings(
        self, blueprint: CourseBlueprint, slide_deck: SlideDeck
    ) -> CheckResult:
        """Validate deterministic step, activity, code, and slide navigation."""

        issues: list[str] = []
        valid_activities = {item.id: item for item in blueprint.activities}
        binding_map = {item.step_id: item for item in slide_deck.step_bindings}
        for step in blueprint.lesson_flow:
            expected_slides = [
                slide for slide in slide_deck.slides if step.id in slide.source_step_ids
            ]
            expected_slide_ids = [slide.id for slide in expected_slides]
            expected_activity_ids = list(
                dict.fromkeys(
                    activity_id
                    for slide in expected_slides
                    for activity_id in slide.activity_ids
                )
            )
            expected_code_ids = list(
                dict.fromkeys(
                    slide.code_example_id
                    for slide in expected_slides
                    if slide.code_example_id
                )
            )
            binding = binding_map.get(step.id)
            if binding is None:
                issues.append(f"{step.id} 缺少 step_bindings 映射")
                continue
            if binding.slide_ids != expected_slide_ids:
                issues.append(f"{step.id} 的 slide_ids 未按实际页面自动生成")
            if binding.activity_ids != expected_activity_ids:
                issues.append(f"{step.id} 的 activity_ids 与实际页面不一致")
            if binding.code_example_ids != expected_code_ids:
                issues.append(f"{step.id} 的 code_example_ids 与实际代码页不一致")
        for slide in slide_deck.slides:
            for activity_id in slide.activity_ids:
                activity = valid_activities.get(activity_id)
                if activity is None:
                    issues.append(f"{slide.id} 引用了不存在的活动 {activity_id}")
                    continue
                if activity.step_ids and not set(slide.source_step_ids) & set(
                    activity.step_ids
                ):
                    issues.append(f"{activity_id} 被绑定到错误环节页面 {slide.id}")
                if (
                    activity.code_example_ids
                    and not any(
                        candidate.code_example_id in activity.code_example_ids
                        for candidate in slide_deck.slides
                        if set(candidate.source_step_ids) & set(activity.step_ids)
                    )
                ):
                    issues.append(
                        f"{activity_id} 所属环节没有引用对应代码页"
                    )
        return self._result(
            "activity_slide_binding",
            issues,
            severe=False,
            scope="execution",
        )

    def _slide_objective_subset(
        self, blueprint: CourseBlueprint, slide_deck: SlideDeck
    ) -> CheckResult:
        """Require slide objectives to be a subset of every source step."""

        steps = {item.id: item for item in blueprint.lesson_flow}
        issues: list[str] = []
        for slide in slide_deck.slides:
            source_steps = [
                steps[step_id]
                for step_id in slide.source_step_ids
                if step_id in steps
            ]
            if not source_steps:
                continue
            allowed = {
                objective_id
                for step in source_steps
                for objective_id in step.objective_ids
            }
            invalid = sorted(set(slide.objective_ids) - allowed)
            if invalid:
                issues.append(
                    f"{slide.id} 的目标 {invalid} 不属于来源 STEP，必须自动恢复"
                )
        for repair in slide_deck.source_repairs:
            issues.append(
                f"{repair.slide_id} 已自动移除非法 {repair.field}: "
                f"{repair.removed_ids}"
            )
        return self._result(
            "slide_objective_subset",
            issues,
            severe=False,
            scope="execution",
        )

    def _student_actions(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        """Compare observable student actions and enforce forbidden operations."""

        issues: list[str] = []
        plan_steps = {item.step_id: item for item in lesson_plan.stages}
        operational_text = "\n".join(
            [
                *(
                    f"{stage.teacher_activity}\n{stage.student_activity}"
                    for stage in lesson_plan.stages
                ),
                *(
                    "\n".join(
                        [
                            slide.title,
                            *slide.content,
                            slide.interaction.prompt,
                            slide.speaker_notes.explanation,
                            slide.speaker_notes.question,
                            slide.speaker_notes.demo,
                            slide.speaker_notes.warning,
                            slide.speaker_notes.transition,
                        ]
                    )
                    for slide in slide_deck.slides
                ),
            ]
        )
        compact_package_text = re.sub(r"\s+", "", operational_text)
        for step in blueprint.lesson_flow:
            action = step.student_action
            if action is None:
                continue
            stage = plan_steps.get(step.id)
            if stage is None:
                continue
            if stage.student_action != action:
                issues.append(f"{step.id} 教案结构化学生活动未继承 Blueprint")
            if stage.student_activity != action.action:
                issues.append(f"{step.id} 教案学生活动与结构化 action 不一致")
            for forbidden in action.forbidden_actions:
                if re.sub(r"\s+", "", forbidden) in compact_package_text:
                    issues.append(f"{step.id} 出现禁止操作“{forbidden}”")
        return self._result(
            "student_action_consistency",
            issues,
            severe=False,
            scope="execution",
        )

    def _exercise_mapping(self, blueprint: CourseBlueprint) -> CheckResult:
        objective_ids = {item.id for item in blueprint.learning_objectives}
        issues = [
            f"{item.id} 没有有效教学目标"
            for item in blueprint.exercises
            if not item.objective_ids or not set(item.objective_ids) <= objective_ids
        ]
        return self._result("exercise_objective_mapping", issues)

    def _exercise_delivery(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> CheckResult:
        """Distinguish teacher-only exercises from student-visible assignments."""

        issues: list[str] = []
        valid = {item.id for item in blueprint.exercises}
        slide_refs = {
            exercise_id
            for slide in slide_deck.slides
            for exercise_id in slide.exercise_ids
        }
        unknown = sorted(slide_refs - valid)
        if unknown:
            issues.append(f"PPT 引用了不存在的练习 {unknown}")
        for exercise in blueprint.exercises:
            on_slide = exercise.id in slide_refs
            if exercise.display_on_slide != on_slide:
                expected = "应展示" if exercise.display_on_slide else "不应展示"
                issues.append(f"{exercise.id} {expected}，但 PPT 标记不一致")
            if (
                exercise.delivery_mode == "teacher_optional"
                and exercise.question in lesson_plan.homework
            ):
                issues.append(f"{exercise.id} 是教师追加练习，不应列为正式课后任务")
            if (
                exercise.delivery_mode
                in {"student_assignment", "extension_challenge"}
                and exercise.question not in lesson_plan.homework
            ):
                issues.append(f"{exercise.id} 应在教案课后任务中明确标记")
        return self._result(
            "exercise_delivery",
            issues,
            severe=False,
            scope="execution",
        )

    def _unknown_slide_knowledge(
        self, blueprint: CourseBlueprint, slide_deck: SlideDeck
    ) -> CheckResult:
        valid = {item.id for item in blueprint.knowledge_points}
        issues = []
        for slide in slide_deck.slides:
            unknown = set(slide.knowledge_ids) - valid
            if unknown:
                issues.append(f"{slide.id} 引用了 Blueprint 外知识点 {sorted(unknown)}")
        return self._result("unknown_slide_knowledge", issues)

    def _unknown_lesson_content(
        self, blueprint: CourseBlueprint, lesson_plan: LessonPlan
    ) -> CheckResult:
        valid_steps = {item.id for item in blueprint.lesson_flow}
        valid_objectives = {item.id for item in blueprint.learning_objectives}
        valid_knowledge = {item.id for item in blueprint.knowledge_points}
        issues = []
        for stage in lesson_plan.stages:
            if stage.step_id not in valid_steps:
                issues.append(f"教案出现 Blueprint 外环节 {stage.step_id}")
            if set(stage.objective_ids) - valid_objectives:
                issues.append(f"{stage.step_id} 出现 Blueprint 外教学目标")
            if set(stage.knowledge_ids) - valid_knowledge:
                issues.append(f"{stage.step_id} 出现 Blueprint 外知识点")
        return self._result("unknown_lesson_content", issues)

    def _interaction_rhythm(self, slide_deck: SlideDeck) -> CheckResult:
        """Require at least one observable learning action in every four content slides."""

        content_slides = [
            slide for slide in slide_deck.slides if slide.slide_type != "cover"
        ]
        issues = []
        for start in range(max(0, len(content_slides) - 3)):
            window = content_slides[start : start + 4]
            if len(window) == 4 and not any(
                slide.interaction and slide.interaction.type != "none"
                for slide in window
            ):
                issues.append(
                    f"{window[0].id}–{window[-1].id} 连续 4 页缺少课堂互动"
                )
        return self._result(
            "slide_interaction_rhythm",
            issues,
            severe=False,
            scope="execution",
        )

    def _text_only_run(self, slide_deck: SlideDeck) -> CheckResult:
        """Detect long runs of passive title-and-text pages."""

        issues: list[str] = []
        run: list[str] = []
        for slide in slide_deck.slides:
            passive = (
                slide.slide_type != "cover"
                and (not slide.interaction or slide.interaction.type == "none")
                and not slide.code_example_id
                and slide.layout not in {"activity", "question", "assignment"}
            )
            if passive:
                run.append(slide.id)
            else:
                if len(run) > 3:
                    issues.append(f"{run[0]}–{run[-1]} 连续纯文字页过多")
                run = []
        if len(run) > 3:
            issues.append(f"{run[0]}–{run[-1]} 连续纯文字页过多")
        return self._result(
            "slide_text_only_run",
            issues,
            severe=False,
            scope="execution",
        )

    def _information_load(self, slide_deck: SlideDeck) -> CheckResult:
        """Keep student-facing pages scannable from a classroom screen."""

        issues = []
        for slide in slide_deck.slides:
            if len(slide.content) > 5:
                issues.append(f"{slide.id} 超过 5 个正文要点")
            if any(len(item) > 120 for item in slide.content):
                issues.append(f"{slide.id} 存在超过 120 字的单个要点")
            if sum(len(item) for item in slide.content) > 360:
                issues.append(f"{slide.id} 正文总量过载")
        return self._result(
            "slide_information_load",
            issues,
            severe=False,
            scope="execution",
        )

    def _lesson_conciseness(
        self, lesson_plan: LessonPlan, slide_deck: SlideDeck
    ) -> CheckResult:
        """Keep the plan a compact execution table instead of a second script."""

        issues = []
        for stage in lesson_plan.stages:
            if len(stage.teacher_activity) > 180:
                issues.append(f"{stage.step_id} 教师活动过长")
            if len(stage.student_activity) > 180:
                issues.append(f"{stage.step_id} 学生活动过长")
            if len(stage.key_question) > 120:
                issues.append(f"{stage.step_id} 关键提问过长")
            if len(stage.assessment) > 180:
                issues.append(f"{stage.step_id} 课堂评价过长")
        lesson_text = lesson_plan.model_dump_json()
        for slide in slide_deck.slides:
            for value in (
                slide.speaker_notes.explanation,
                slide.speaker_notes.demo,
                slide.speaker_notes.transition,
            ):
                if len(value) >= 45 and value in lesson_text:
                    issues.append(f"教案重复了 {slide.id} 的完整逐页讲解提示")
        return self._result(
            "lesson_plan_conciseness",
            issues,
            severe=False,
            scope="execution",
        )

    def _speaker_notes_conciseness(self, slide_deck: SlideDeck) -> CheckResult:
        """Reject notes that drift into paragraph-style speech scripts."""

        issues = []
        for slide in slide_deck.slides:
            notes = slide.speaker_notes
            total = sum(
                len(value)
                for value in (
                    notes.explanation,
                    notes.question,
                    notes.demo,
                    notes.warning,
                    notes.transition,
                )
            )
            if total > 500:
                issues.append(f"{slide.id} 逐页讲解提示过长，接近逐字稿")
            if any(
                value.count("。") + value.count("！") + value.count("？") > 3
                for value in (
                    notes.explanation,
                    notes.question,
                    notes.demo,
                    notes.warning,
                    notes.transition,
                )
            ):
                issues.append(f"{slide.id} 逐页讲解提示包含过多完整句")
        return self._result(
            "speaker_notes_conciseness",
            issues,
            severe=False,
            scope="execution",
        )
