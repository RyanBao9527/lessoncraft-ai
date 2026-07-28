"""User input model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourseInput(BaseModel):
    """Raw course requirements supplied by a teacher."""

    model_config = ConfigDict(str_strip_whitespace=True)

    language: Literal["Python", "Scratch", "C++"]
    topic: str = Field(min_length=2, max_length=100)
    age_range: str = Field(min_length=2, max_length=40)
    student_level: str = Field(min_length=2, max_length=300)
    duration_minutes: int = Field(ge=30, le=240)
    core_goal: str = Field(min_length=4, max_length=300)
    teaching_style: Literal["互动实践型", "项目驱动型", "游戏化", "基础讲解型"]
    max_slides: int = Field(default=15, ge=5, le=30)
    additional_requirements: str = Field(default="", max_length=1000)

    @field_validator("topic", "student_level", "core_goal")
    @classmethod
    def reject_placeholder_text(cls, value: str) -> str:
        """Reject empty-looking placeholders that pass a length check."""

        if set(value) <= {"-", "_", " "}:
            raise ValueError("请输入有效内容")
        return value
