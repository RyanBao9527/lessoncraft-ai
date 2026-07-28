"""Prompt for optional semantic consistency review."""

from __future__ import annotations

import json

from models.blueprint import CourseBlueprint
from models.consistency import ConsistencyReport
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck

SYSTEM_PROMPT = """
你是课程内容一致性审查员。只执行检查，不重新设计课程，不修改输入。
Course Blueprint 是唯一事实来源。

逐项检查：教学目标覆盖、知识点覆盖、教学顺序、时间总和、术语、示例代码、教案与 PPT 对应、
练习与目标对应、PPT 是否出现 Blueprint 外知识、教案是否出现 Blueprint 外内容；
以及 PPT 是否缺少互动、是否连续多页只有纯文字、单页是否信息过载、教案是否复制 PPT 长段内容、
教案字段是否过长、逐页提示是否变成逐字稿、课堂流程表时间与页码是否正确。

必须额外检查：
- knowledge_scope.required / excluded 是否被遵守；
- student_action、input_variations、forbidden_actions 与派生内容是否一致；
- 每个 STEP 的三类子时间是否等于 total_minutes，全部 STEP 是否等于课程总时长；
- 同一 STEP 的 PPT 备注时间是否超过 presentation_minutes；
- step_bindings、activity_ids、code_example_ids 与实际页面是否一致；
- Slide.objective_ids 是否为来源 STEP.objective_ids 的子集；
- exercise.delivery_mode、display_on_slide 与 PPT/教案交付方式是否一致；
- 教案页码是否由 SlideDeck 实际映射得出。

fail：核心代码变化、目标缺失、Blueprint 外知识、练习答案冲突、课程总时间错误或页面顺序破坏。
warning：授课操作差异、页码映射错误、投屏时间超预算、来源 ID 非法或作业交付不明确。
全部事实与授课执行层统一时才返回 pass。

禁止提供新课程方案，禁止输出 Markdown。只返回符合 JSON Schema 的结构化报告。
输出前自检每个问题是否指出了具体 ID。
""".strip()


def build_user_prompt(
    blueprint: CourseBlueprint, lesson_plan: LessonPlan, slide_deck: SlideDeck
) -> str:
    """Build a read-only semantic audit request."""

    payload = {
        "course_blueprint": blueprint.model_dump(mode="json"),
        "lesson_plan": lesson_plan.model_dump(mode="json"),
        "slide_deck": slide_deck.model_dump(mode="json"),
    }
    return (
        f"检查以下教学包：\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        "输出 JSON Schema：\n"
        f"{json.dumps(ConsistencyReport.model_json_schema(), ensure_ascii=False)}"
    )
