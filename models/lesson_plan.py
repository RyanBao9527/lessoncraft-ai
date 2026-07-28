"""Teacher-facing lesson plan models."""

from typing import Literal

from pydantic import Field, model_validator

from .blueprint import StepDuration, StrictModel, StudentAction


class LessonPlanStage(StrictModel):
    step_id: str = Field(pattern=r"^STEP-\d{2}$")
    title: str
    duration_minutes: int = Field(gt=0)
    duration: StepDuration | None = None
    objective_ids: list[str] = Field(min_length=1)
    knowledge_ids: list[str] = Field(default_factory=list)
    teacher_activity: str = Field(max_length=180)
    student_activity: str = Field(max_length=180)
    student_action: StudentAction | None = None
    key_question: str = Field(max_length=120)
    assessment: str = Field(max_length=180)
    slide_ids: list[str] = Field(default_factory=list)
    materials_or_code: list[str] = Field(default_factory=list, max_length=6)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_duration(cls, data: object) -> object:
        """Keep old LessonPlan JSON readable during the compatibility window."""

        if not isinstance(data, dict) or data.get("duration") is not None:
            return data
        migrated = dict(data)
        total = int(migrated.get("duration_minutes", 0))
        presentation = max(1, round(total * 0.45))
        transition = 1 if total >= 5 else 0
        migrated["duration"] = {
            "total_minutes": total,
            "presentation_minutes": presentation,
            "student_practice_minutes": total - presentation - transition,
            "transition_minutes": transition,
        }
        return migrated

    @model_validator(mode="after")
    def keep_duration_aligned(self) -> "LessonPlanStage":
        if self.duration is None:
            raise ValueError("duration 为必填结构")
        if self.duration.total_minutes != self.duration_minutes:
            raise ValueError("教案 duration.total_minutes 必须等于 duration_minutes")
        return self


class LessonPlan(StrictModel):
    """Concise course navigation and execution plan derived from a Blueprint."""

    plan_type: Literal["concise"] = "concise"
    course_overview: str
    teaching_objectives: list[str] = Field(min_length=1)
    key_points: list[str] = Field(min_length=1)
    difficult_points: list[str] = Field(default_factory=list)
    preparation: list[str] = Field(default_factory=list)
    stages: list[LessonPlanStage] = Field(min_length=1)
    classroom_assessment: list[str] = Field(default_factory=list)
    homework: list[str] = Field(default_factory=list)
    teacher_reminders: list[str] = Field(default_factory=list)
    code_example_ids: list[str] = Field(default_factory=list)
