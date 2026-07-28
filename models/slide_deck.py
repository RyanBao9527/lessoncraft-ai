"""Student-facing slide deck models with classroom-action metadata."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .blueprint import StrictModel

ShortSlideText = Annotated[str, Field(max_length=120)]


class SpeakerNotes(StrictModel):
    """Per-slide teaching prompts, not a verbatim script."""

    explanation: str = Field(default="", max_length=180)
    question: str = Field(default="", max_length=120)
    demo: str = Field(default="", max_length=150)
    warning: str = Field(default="", max_length=120)
    transition: str = Field(default="", max_length=120)
    suggested_minutes: int = Field(default=2, ge=1, le=20)


class SlideInteraction(StrictModel):
    """One concise observable classroom interaction."""

    type: Literal[
        "none",
        "question",
        "prediction",
        "choice",
        "fill_blank",
        "debug",
        "hands_on",
        "reflection",
    ] = "none"
    prompt: str = Field(default="", max_length=120)
    expected_response: str = Field(default="", max_length=150)


class CodeDisplay(StrictModel):
    """How an existing Blueprint code example should appear on this page."""

    code_example_id: str = Field(pattern=r"^CODE-\d{2}$")
    highlight_lines: list[int] = Field(default_factory=list, max_length=12)
    reveal_step: int = Field(default=1, ge=1, le=6)


class Slide(StrictModel):
    id: str = Field(pattern=r"^SLIDE-\d{2}$")
    title: str
    layout: Literal[
        "title",
        "title_and_content",
        "objectives",
        "scenario",
        "knowledge",
        "code",
        "activity",
        "exercise",
        "summary",
        "homework",
        "section",
        "question",
        "concept",
        "comparison",
        "assignment",
    ] = "title_and_content"
    slide_type: Literal[
        "cover",
        "scenario",
        "challenge",
        "review",
        "question",
        "concept",
        "process",
        "code_minimal",
        "code_step",
        "prediction",
        "interaction",
        "activity",
        "error",
        "project",
        "upgrade",
        "summary",
        "assignment",
    ] = "concept"
    learning_action: Literal[
        "observe",
        "recall",
        "predict",
        "discuss",
        "explain",
        "code",
        "debug",
        "practice",
        "reflect",
        "create",
    ] = "observe"
    visual_direction: str = Field(default="", max_length=160)
    content: list[ShortSlideText] = Field(default_factory=list, max_length=5)
    source_step_ids: list[str] = Field(default_factory=list)
    objective_ids: list[str] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    code_example_id: str | None = None
    activity_ids: list[str] = Field(default_factory=list)
    exercise_ids: list[str] = Field(default_factory=list)
    interaction: SlideInteraction = Field(default_factory=SlideInteraction)
    code_display: CodeDisplay | None = None
    speaker_notes: SpeakerNotes

    @model_validator(mode="after")
    def keep_code_references_aligned(self) -> "Slide":
        """Keep the legacy code ID and new display metadata compatible."""

        if self.code_display and self.code_example_id is None:
            self.code_example_id = self.code_display.code_example_id
        if (
            self.code_display
            and self.code_example_id
            and self.code_display.code_example_id != self.code_example_id
        ):
            raise ValueError("code_display 与 code_example_id 必须引用同一代码示例")
        return self


class StepSlideBinding(StrictModel):
    """Deterministic navigation from one Blueprint step to its slide assets."""

    step_id: str = Field(pattern=r"^STEP-\d{2}$")
    slide_ids: list[str] = Field(default_factory=list)
    activity_ids: list[str] = Field(default_factory=list)
    code_example_ids: list[str] = Field(default_factory=list)


class SourceRepair(StrictModel):
    """Visible audit trail for an automatically repaired source-ID violation."""

    slide_id: str = Field(pattern=r"^SLIDE-\d{2}$")
    field: Literal["objective_ids", "knowledge_ids"]
    removed_ids: list[str] = Field(min_length=1)
    reason: str = Field(min_length=2)


class SlideDeck(StrictModel):
    """A bounded set of slides derived from the Blueprint."""

    title: str
    slides: list[Slide] = Field(min_length=1)
    step_bindings: list[StepSlideBinding] = Field(default_factory=list)
    source_repairs: list[SourceRepair] = Field(default_factory=list)
