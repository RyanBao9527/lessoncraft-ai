"""Blueprint-first revision workflow."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.blueprint import CourseBlueprint, StepDuration
from prompts.revision_prompt import SYSTEM_PROMPT, build_user_prompt

from .consistency_checker import ConsistencyChecker
from .course_generator import (
    CourseGenerator,
    derive_lesson_plan,
    derive_slide_deck,
    sync_lesson_slide_ids,
)
from .llm_client import LLMClient


class RevisionResult(BaseModel):
    """Validated revision envelope returned by either mode."""

    model_config = ConfigDict(extra="forbid")

    change_summary: str
    affected_ids: list[str] = Field(default_factory=list)
    updated_blueprint: CourseBlueprint


class RevisionService:
    """Update the Blueprint first and regenerate every derived artifact."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def revise_blueprint(
        self, blueprint: CourseBlueprint, revision_request: str
    ) -> RevisionResult:
        """Use the configured LLM to make a validated Blueprint-only revision."""

        if not revision_request.strip():
            raise ValueError("请输入修改要求")
        if self.llm_client is None:
            return self._demo_revision(blueprint, revision_request)
        data = self.llm_client.generate_json(
            SYSTEM_PROMPT, build_user_prompt(blueprint, revision_request)
        )
        return RevisionResult.model_validate(data)

    def revise_package(
        self, blueprint: CourseBlueprint, revision_request: str
    ) -> dict[str, Any]:
        """Revise canonical data, regenerate derived content, then recheck."""

        revision = self.revise_blueprint(blueprint, revision_request)
        updated = revision.updated_blueprint
        if self.llm_client is None:
            slide_deck = derive_slide_deck(updated)
            lesson_plan = derive_lesson_plan(updated, slide_deck)
            report = ConsistencyChecker().check(updated, lesson_plan, slide_deck)
        else:
            generator = CourseGenerator(self.llm_client)
            lesson_plan = generator.generate_lesson_plan(updated)
            slide_deck = generator.generate_slide_deck(updated)
            lesson_plan = sync_lesson_slide_ids(lesson_plan, slide_deck, updated)
            report = generator.generate_consistency_report(
                updated, lesson_plan, slide_deck
            )
        return {
            "revision": revision.model_dump(mode="json", exclude={"updated_blueprint"}),
            "blueprint": updated.model_dump(mode="json"),
            "lesson_plan": lesson_plan.model_dump(mode="json"),
            "slide_deck": slide_deck.model_dump(mode="json"),
            "consistency_report": report.model_dump(mode="json"),
        }

    @staticmethod
    def _demo_revision(
        blueprint: CourseBlueprint, revision_request: str
    ) -> RevisionResult:
        """Apply a transparent deterministic revision for offline demonstration."""

        updated = blueprint.model_copy(deep=True)
        affected = [
            *[item.id for item in updated.lesson_flow],
            *[item.id for item in updated.code_examples],
            *[item.id for item in updated.activities],
            *[item.id for item in updated.exercises],
        ]
        summary_parts: list[str] = []
        duration_match = re.search(r"(\d{2,3})\s*分钟", revision_request)
        if duration_match:
            new_duration = int(duration_match.group(1))
            if 30 <= new_duration <= 240:
                old_duration = updated.course.duration_minutes
                updated.course.duration_minutes = new_duration
                scaled = [
                    max(5, round(step.duration_minutes * new_duration / old_duration))
                    for step in updated.lesson_flow
                ]
                difference = new_duration - sum(scaled)
                cursor = 0
                while difference:
                    index = cursor % len(scaled)
                    if difference > 0:
                        scaled[index] += 1
                        difference -= 1
                    elif scaled[index] > 5:
                        scaled[index] -= 1
                        difference += 1
                    cursor += 1
                for step, minutes in zip(updated.lesson_flow, scaled, strict=True):
                    original = step.duration
                    step.duration_minutes = minutes
                    presentation = max(
                        1,
                        round(
                            minutes
                            * original.presentation_minutes
                            / original.total_minutes
                        ),
                    )
                    transition = min(
                        max(
                            0,
                            round(
                                minutes
                                * original.transition_minutes
                                / original.total_minutes
                            ),
                        ),
                        max(0, minutes - presentation),
                    )
                    step.duration = StepDuration(
                        total_minutes=minutes,
                        presentation_minutes=presentation,
                        student_practice_minutes=minutes
                        - presentation
                        - transition,
                        transition_minutes=transition,
                    )
                summary_parts.append(f"课程时长更新为 {new_duration} 分钟")
        if "游戏化" in revision_request:
            updated.course.teaching_style = "游戏化"
            summary_parts.append("教学风格更新为游戏化")
        elif "项目驱动" in revision_request:
            updated.course.teaching_style = "项目驱动型"
            summary_parts.append("教学风格更新为项目驱动型")
        updated.revision_notes.append(revision_request.strip())
        if not summary_parts:
            summary_parts.append("已记录补充要求，并标记全部派生内容重新生成")
        return RevisionResult(
            change_summary="；".join(summary_parts),
            affected_ids=sorted(set(affected)),
            updated_blueprint=updated,
        )
