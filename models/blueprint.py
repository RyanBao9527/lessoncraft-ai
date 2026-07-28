"""Course Blueprint: the single source of truth."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID_PATTERNS = {
    "objective": r"^OBJ-\d{2}$",
    "knowledge": r"^K-\d{2}$",
    "step": r"^STEP-\d{2}$",
    "code": r"^CODE-\d{2}$",
    "activity": r"^ACT-\d{2}$",
    "exercise": r"^EX-\d{2}$",
}


class StrictModel(BaseModel):
    """Shared strict model configuration for generated JSON."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CourseMeta(StrictModel):
    title: str = Field(min_length=2)
    language: Literal["Python", "Scratch", "C++"]
    age_range: str = Field(min_length=2)
    student_level: str = Field(min_length=2)
    duration_minutes: int = Field(ge=30, le=240)
    core_goal: str = Field(min_length=4)
    teaching_style: Literal["互动实践型", "项目驱动型", "游戏化", "基础讲解型"]
    max_slides: int = Field(default=15, ge=5, le=30)
    additional_requirements: str = ""


class TerminologyItem(StrictModel):
    term: str = Field(min_length=1)
    standard_definition: str = Field(min_length=2)


class LearningObjective(StrictModel):
    id: str = Field(pattern=ID_PATTERNS["objective"])
    content: str = Field(min_length=4)
    assessment: str = Field(min_length=4)


class KnowledgePoint(StrictModel):
    id: str = Field(pattern=ID_PATTERNS["knowledge"])
    name: str = Field(min_length=1)
    definition: str = Field(min_length=2)
    objective_ids: list[str] = Field(min_length=1)
    common_errors: list[str] = Field(default_factory=list)


class KnowledgeScope(StrictModel):
    """Explicitly bound the concepts that may be taught in this course."""

    required: list[str] = Field(default_factory=list)
    mentioned_only: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def keep_scope_disjoint(self) -> "KnowledgeScope":
        groups = {
            "required": set(self.required),
            "mentioned_only": set(self.mentioned_only),
            "excluded": set(self.excluded),
        }
        if groups["required"] & groups["mentioned_only"]:
            raise ValueError("required 与 mentioned_only 不可重复")
        if groups["required"] & groups["excluded"]:
            raise ValueError("required 与 excluded 不可重复")
        if groups["mentioned_only"] & groups["excluded"]:
            raise ValueError("mentioned_only 与 excluded 不可重复")
        return self


class StepDuration(StrictModel):
    """Separate whole-stage time from projected explanation time."""

    total_minutes: int = Field(gt=0, le=120)
    presentation_minutes: int = Field(ge=0, le=120)
    student_practice_minutes: int = Field(ge=0, le=120)
    transition_minutes: int = Field(ge=0, le=30)

    @model_validator(mode="after")
    def validate_parts(self) -> "StepDuration":
        parts = (
            self.presentation_minutes
            + self.student_practice_minutes
            + self.transition_minutes
        )
        if parts != self.total_minutes:
            raise ValueError(
                "presentation_minutes、student_practice_minutes、"
                "transition_minutes 之和必须等于 total_minutes"
            )
        return self


class StudentAction(StrictModel):
    """Observable student action with explicit safe and forbidden operations."""

    action: str = Field(min_length=2, max_length=180)
    input_variations: list[str] = Field(default_factory=list, max_length=8)
    forbidden_actions: list[str] = Field(default_factory=list, max_length=8)
    expected_evidence: str = Field(default="", max_length=180)


class LessonFlowStep(StrictModel):
    id: str = Field(pattern=ID_PATTERNS["step"])
    title: str = Field(min_length=2)
    duration_minutes: int = Field(gt=0, le=120)
    duration: StepDuration | None = None
    objective_ids: list[str] = Field(min_length=1)
    knowledge_ids: list[str] = Field(default_factory=list)
    teacher_activity: str = Field(min_length=2)
    student_activity: str = Field(min_length=2)
    student_action: StudentAction | None = None
    key_question: str = Field(min_length=2)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_duration(cls, data: object) -> object:
        """Accept old Blueprint JSON while emitting the structured duration."""

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
    def keep_legacy_duration_aligned(self) -> "LessonFlowStep":
        if self.duration is None:
            raise ValueError("duration 为必填结构")
        if self.duration.total_minutes != self.duration_minutes:
            raise ValueError("duration.total_minutes 必须等于 duration_minutes")
        return self


class CodeExample(StrictModel):
    id: str = Field(pattern=ID_PATTERNS["code"])
    title: str = Field(min_length=2)
    language: Literal["python", "scratch", "cpp"]
    code: str = Field(min_length=1)
    explanation: str = Field(min_length=2)
    objective_ids: list[str] = Field(min_length=1)
    knowledge_ids: list[str] = Field(default_factory=list)


class Activity(StrictModel):
    id: str = Field(pattern=ID_PATTERNS["activity"])
    title: str = Field(min_length=2)
    instructions: str = Field(min_length=2)
    duration_minutes: int = Field(gt=0, le=90)
    objective_ids: list[str] = Field(min_length=1)
    step_ids: list[str] = Field(default_factory=list)
    code_example_ids: list[str] = Field(default_factory=list)


class Exercise(StrictModel):
    id: str = Field(pattern=ID_PATTERNS["exercise"])
    question: str = Field(min_length=2)
    answer: str = Field(min_length=1)
    difficulty: Literal["基础", "进阶", "挑战"]
    objective_ids: list[str] = Field(min_length=1)
    delivery_mode: Literal[
        "in_class",
        "student_assignment",
        "teacher_optional",
        "extension_challenge",
    ] = "in_class"
    display_on_slide: bool = False


class CourseBlueprint(StrictModel):
    """Canonical course definition from which all deliverables derive."""

    course: CourseMeta
    knowledge_scope: KnowledgeScope = Field(default_factory=KnowledgeScope)
    terminology: list[TerminologyItem] = Field(min_length=1)
    learning_objectives: list[LearningObjective] = Field(min_length=1)
    knowledge_points: list[KnowledgePoint] = Field(min_length=1)
    lesson_flow: list[LessonFlowStep] = Field(min_length=1)
    code_examples: list[CodeExample] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list)
    revision_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ids_and_references(self) -> CourseBlueprint:
        """Ensure IDs are unique and every cross-reference exists."""

        groups = [
            self.learning_objectives,
            self.knowledge_points,
            self.lesson_flow,
            self.code_examples,
            self.activities,
            self.exercises,
        ]
        for group in groups:
            ids = [item.id for item in group]
            if len(ids) != len(set(ids)):
                raise ValueError(f"ID 不可重复: {ids}")

        objective_ids = {item.id for item in self.learning_objectives}
        knowledge_ids = {item.id for item in self.knowledge_points}
        step_ids = {item.id for item in self.lesson_flow}
        code_ids = {item.id for item in self.code_examples}
        for item in [
            *self.knowledge_points,
            *self.lesson_flow,
            *self.code_examples,
            *self.activities,
            *self.exercises,
        ]:
            unknown = set(item.objective_ids) - objective_ids
            if unknown:
                raise ValueError(f"{item.id} 引用了不存在的教学目标: {sorted(unknown)}")
        for item in [*self.lesson_flow, *self.code_examples]:
            unknown = set(item.knowledge_ids) - knowledge_ids
            if unknown:
                raise ValueError(f"{item.id} 引用了不存在的知识点: {sorted(unknown)}")
        for item in self.activities:
            unknown_steps = set(item.step_ids) - step_ids
            if unknown_steps:
                raise ValueError(f"{item.id} 引用了不存在的环节: {sorted(unknown_steps)}")
            unknown_codes = set(item.code_example_ids) - code_ids
            if unknown_codes:
                raise ValueError(f"{item.id} 引用了不存在的代码: {sorted(unknown_codes)}")
        return self
