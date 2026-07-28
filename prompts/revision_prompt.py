"""Prompt for Blueprint-first revisions."""

from __future__ import annotations

import json
from typing import Any

from models.blueprint import CourseBlueprint

SYSTEM_PROMPT = """
你是课程版本编辑器。所有修改必须先发生在 Course Blueprint，再由系统重新生成派生内容。

输入是原始 Blueprint 和教师修改要求。返回 change_summary、affected_ids、updated_blueprint。
affected_ids 必须列出被直接修改或因依赖关系需要重新生成的 Blueprint ID。

禁止：直接修改教案或 PPT；返回 Blueprint 外知识；破坏 ID 引用；静默修改未受影响内容；
改写未被要求修改的示例代码。修改后仍须满足知识范围、结构化学生操作、STEP 时间拆分、
练习交付方式、目标覆盖、术语和引用一致性。修改术语时同步维护 aliases 且不得产生冲突；
修改知识范围时保证每个 required 有正式内容、mentioned_only 不被提升、excluded 不进入
派生内容；修改练习时遵守 delivery_mode 与 display_on_slide 的固定矩阵。调整课程时长时
必须同步更新 duration 的三个子时间，且所有 STEP 总时间严格等于课程时长。

只输出 JSON，不使用 Markdown。输出前自检 updated_blueprint 可通过原 Blueprint Schema 校验。
""".strip()


def revision_schema() -> dict[str, Any]:
    """Return the exact wrapper schema expected from revision calls."""

    return {
        "type": "object",
        "required": ["change_summary", "affected_ids", "updated_blueprint"],
        "properties": {
            "change_summary": {"type": "string"},
            "affected_ids": {"type": "array", "items": {"type": "string"}},
            "updated_blueprint": CourseBlueprint.model_json_schema(),
        },
        "additionalProperties": False,
    }


def build_user_prompt(blueprint: CourseBlueprint, revision_request: str) -> str:
    """Build the Blueprint revision request."""

    return (
        f"原始 Blueprint：\n{blueprint.model_dump_json(indent=2)}\n\n"
        f"教师修改要求：\n{revision_request.strip()}\n\n"
        "输出 JSON Schema：\n"
        f"{json.dumps(revision_schema(), ensure_ascii=False)}"
    )
