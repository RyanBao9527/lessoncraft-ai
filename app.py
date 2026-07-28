"""LessonCraft AI Streamlit MVP."""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from exporters.docx_exporter import export_lesson_plan_docx
from exporters.pptx_exporter import export_slide_deck_pptx
from models.blueprint import CourseBlueprint
from models.consistency import ConsistencyReport
from models.course_input import CourseInput
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck
from services.consistency_checker import ConsistencyChecker
from services.course_generator import CourseGenerator, sync_lesson_slide_ids
from services.llm_client import LLMClient, LLMConfigurationError, LLMGenerationError
from services.revision_service import RevisionService
from utils.file_manager import load_demo_package, safe_filename

load_dotenv()

st.set_page_config(
    page_title="LessonCraft AI",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem;}
    .hero {
        padding: 2rem 2.2rem; border-radius: 24px;
        background: linear-gradient(135deg, #17365d 0%, #2e74b5 68%, #5d9bd3 100%);
        color: white; margin-bottom: 1.4rem;
    }
    .hero h1 {font-size: 2.55rem; margin: 0 0 .45rem 0;}
    .hero p {font-size: 1.08rem; margin: .2rem 0; opacity: .95;}
    .eyebrow {letter-spacing: .12em; text-transform: uppercase; font-size: .76rem;}
    .demo-banner {
        border-left: 5px solid #ffc74a; padding: .7rem 1rem;
        background: #fff8e8; border-radius: 8px; color: #594300; margin: .7rem 0 1.2rem;
    }
    .slide-card {
        border: 1px solid #dce7f1; border-radius: 16px; padding: 1.2rem 1.4rem;
        background: #fbfdff; min-height: 180px; margin-bottom: .8rem;
    }
    .slide-id {color: #64748b; font-size: .78rem; letter-spacing: .08em;}
    div[data-testid="stMetric"] {background: #f5f9fc; padding: .7rem; border-radius: 12px;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <div class="eyebrow">Blueprint-first teaching package</div>
  <h1>LessonCraft AI</h1>
  <p><strong>少儿编程教学包生成 Skill</strong></p>
  <p>输入课程主题、年龄、基础与课时，一次生成内容一致的教案、课件、逐页提示、代码和练习。</p>
</div>
""",
    unsafe_allow_html=True,
)
st.caption("使用方法：填写课程信息 → 生成并检查 → 在 Tabs 中预览 → 提出修改 → 下载可编辑文件")

api_ready = bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL"))
demo_mode = st.toggle(
    "Demo Mode（不调用模型 API）",
    value=not api_ready,
    help="使用仓库内固定样例，可完整预览和导出。",
)
if demo_mode:
    st.markdown(
        '<div class="demo-banner"><strong>当前为演示模式</strong>：使用 '
        "examples/sample_output/ 中的固定“Python 猜数字游戏”样例，不调用真实模型。</div>",
        unsafe_allow_html=True,
    )
elif not api_ready:
    st.warning("尚未配置 LLM_API_KEY 和 LLM_MODEL。请启用 Demo Mode，或先配置 .env。")


def _parse_package(package: dict[str, Any]) -> tuple[
    CourseBlueprint, LessonPlan, SlideDeck, ConsistencyReport
]:
    return (
        CourseBlueprint.model_validate(package["blueprint"]),
        LessonPlan.model_validate(package["lesson_plan"]),
        SlideDeck.model_validate(package["slide_deck"]),
        ConsistencyReport.model_validate(package["consistency_report"]),
    )


def _save_package(package: dict[str, Any], is_demo: bool) -> None:
    st.session_state["package"] = package
    st.session_state["package_is_demo"] = is_demo


st.subheader("1. 课程信息")
with st.form("course_form"):
    row1 = st.columns([1, 2, 1])
    language = row1[0].selectbox("编程语言", ["Python", "Scratch", "C++"])
    topic = row1[1].text_input("课程主题", value="猜数字游戏")
    age_range = row1[2].text_input("学生年龄", value="10～12 岁")

    row2 = st.columns([2, 1, 1])
    student_level = row2[0].text_input("学生基础", value="学过变量、input 和 if")
    duration_minutes = row2[1].number_input(
        "课程时长（分钟）", min_value=30, max_value=240, value=90, step=5
    )
    teaching_style = row2[2].selectbox(
        "教学风格", ["互动实践型", "项目驱动型", "游戏化", "基础讲解型"]
    )

    core_goal = st.text_input("核心教学目标", value="理解并使用 while 循环")
    max_slides = st.slider("PPT 页数上限", min_value=5, max_value=30, value=15)
    additional_requirements = st.text_area(
        "补充要求（可选）", value="课堂最后完成一个完整小游戏", height=80
    )
    generate_clicked = st.form_submit_button(
        "生成完整教学包", type="primary", width="stretch"
    )

if generate_clicked:
    try:
        course_input = CourseInput(
            language=language,
            topic=topic,
            age_range=age_range,
            student_level=student_level,
            duration_minutes=duration_minutes,
            core_goal=core_goal,
            teaching_style=teaching_style,
            max_slides=max_slides,
            additional_requirements=additional_requirements,
        )
        with st.status("正在生成教学包…", expanded=True) as status:
            status.write("正在分析课程需求")
            if demo_mode:
                status.write("正在生成课程母稿")
                package = load_demo_package()
                status.write("正在生成教案")
                status.write("正在生成 PPT")
                status.write("正在检查内容一致性")
            else:
                client = LLMClient()
                generator = CourseGenerator(client)
                status.write("正在生成课程母稿")
                blueprint = generator.generate_blueprint(course_input)
                status.write("正在生成教案")
                lesson_plan = generator.generate_lesson_plan(blueprint)
                status.write("正在生成 PPT")
                slide_deck = generator.generate_slide_deck(blueprint)
                lesson_plan = sync_lesson_slide_ids(
                    lesson_plan, slide_deck, blueprint
                )
                status.write("正在检查内容一致性")
                report = generator.generate_consistency_report(
                    blueprint, lesson_plan, slide_deck
                )
                package = {
                    "course_input": course_input.model_dump(mode="json"),
                    "blueprint": blueprint.model_dump(mode="json"),
                    "lesson_plan": lesson_plan.model_dump(mode="json"),
                    "slide_deck": slide_deck.model_dump(mode="json"),
                    "consistency_report": report.model_dump(mode="json"),
                }
            status.update(label="生成完成", state="complete", expanded=False)
        _save_package(package, demo_mode)
        st.success("教学包已生成，可在下方预览、修改和导出。")
    except (ValidationError, ValueError, LLMConfigurationError, LLMGenerationError) as exc:
        st.error(f"生成失败：{exc}")
    except Exception as exc:
        st.exception(exc)


if "package" in st.session_state:
    package = st.session_state["package"]
    blueprint, lesson_plan, slide_deck, report = _parse_package(package)

    st.subheader("2. 结果预览")
    tabs = st.tabs(
        [
            "课程母稿",
            "教案",
            "PPT 页面",
            "教师逐页讲解提示",
            "示例代码",
            "练习题",
            "一致性报告",
        ]
    )
    with tabs[0]:
        metrics = st.columns(4)
        metrics[0].metric("教学目标", len(blueprint.learning_objectives))
        metrics[1].metric("知识点", len(blueprint.knowledge_points))
        metrics[2].metric("课堂环节", len(blueprint.lesson_flow))
        metrics[3].metric(
            "计划时长",
            f"{sum(s.duration.total_minutes for s in blueprint.lesson_flow)} 分钟",
        )
        st.json(blueprint.model_dump(mode="json"), expanded=False)

    with tabs[1]:
        st.caption("精简授课版：用于 2～3 分钟快速掌握课堂节奏。")
        st.caption(
            "教案时间包含讲解、学生操作、巡视和过渡；"
            "PPT 备注时间仅表示逐页投屏讲解建议时间。"
        )
        st.markdown(f"**课程概览**：{lesson_plan.course_overview}")
        st.markdown(
            f"**目标**：{'；'.join(lesson_plan.teaching_objectives)}  \n"
            f"**重点**：{'；'.join(lesson_plan.key_points)}  \n"
            f"**难点**：{'；'.join(lesson_plan.difficult_points) or '无'}"
        )
        st.dataframe(
            [
                {
                    "时间": f"{stage.duration.total_minutes} 分钟",
                    "对应PPT页": "、".join(stage.slide_ids) or "—",
                    "教学环节": stage.title,
                    "教师活动": stage.teacher_activity,
                    "学生活动": stage.student_activity,
                    "对应目标": "、".join(stage.objective_ids),
                    "材料或代码": "、".join(stage.materials_or_code) or "—",
                }
                for stage in lesson_plan.stages
            ],
            hide_index=True,
            width="stretch",
        )

    with tabs[2]:
        for slide in slide_deck.slides:
            content = "".join(f"<li>{item}</li>" for item in slide.content)
            st.markdown(
                f'<div class="slide-card"><div class="slide-id">{slide.id} · '
                f'{slide.slide_type} · {slide.learning_action}</div>'
                f'<h3>{slide.title}</h3><ul>{content}</ul></div>',
                unsafe_allow_html=True,
            )
            if slide.interaction and slide.interaction.type != "none":
                st.info(
                    f"课堂互动 · {slide.interaction.type}："
                    f"{slide.interaction.prompt}"
                )
            st.caption(
                f"来源步骤：{', '.join(slide.source_step_ids) or '无'} ｜ "
                f"目标：{', '.join(slide.objective_ids) or '无'} ｜ "
                f"知识：{', '.join(slide.knowledge_ids) or '无'}"
            )

    with tabs[3]:
        for slide in slide_deck.slides:
            notes = slide.speaker_notes
            with st.expander(f"{slide.id} · {slide.title}"):
                st.markdown(f"**讲解重点**：{notes.explanation or '—'}")
                st.markdown(f"**课堂提问**：{notes.question or '—'}")
                st.markdown(f"**演示动作**：{notes.demo or '—'}")
                st.markdown(f"**常见错误**：{notes.warning or '—'}")
                st.markdown(f"**时间建议**：{notes.suggested_minutes} 分钟")
                st.markdown(f"**下一页过渡**：{notes.transition or '—'}")

    with tabs[4]:
        for example in blueprint.code_examples:
            st.markdown(f"#### {example.id} · {example.title}")
            language_key = {"python": "python", "cpp": "cpp", "scratch": "text"}[
                example.language
            ]
            st.code(example.code, language=language_key)
            st.caption(example.explanation)

    with tabs[5]:
        for exercise in blueprint.exercises:
            with st.expander(f"{exercise.id} · {exercise.difficulty} · {exercise.question}"):
                st.markdown(f"**参考答案**：{exercise.answer}")
                delivery_labels = {
                    "in_class": "课堂检查",
                    "student_assignment": "学生正式作业",
                    "teacher_optional": "教师追加提问/补充练习",
                    "extension_challenge": "投屏展示的拓展挑战",
                }
                st.caption(
                    f"交付方式：{delivery_labels[exercise.delivery_mode]} ｜ "
                    f"学生 PPT 展示：{'是' if exercise.display_on_slide else '否'} ｜ "
                    f"对应目标：{', '.join(exercise.objective_ids)}"
                )

    with tabs[6]:
        status_label = {"pass": "通过", "warning": "有提醒", "fail": "未通过"}[
            report.status
        ]
        if report.status == "pass":
            st.success(f"一致性状态：{status_label}")
        elif report.status == "warning":
            st.warning(f"一致性状态：{status_label}")
        else:
            st.error(f"一致性状态：{status_label}")
        for check in report.checks:
            icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}[check.status]
            st.markdown(f"{icon} **{check.name}**")
            for issue in check.issues:
                st.write(f"— {issue}")

    st.subheader("3. 修改教学包")
    revision_request = st.text_area(
        "请输入修改要求",
        placeholder="例如：把课程改成 100 分钟，并增加更多游戏化互动。",
        key="revision_request",
    )
    if st.button("更新教学包", type="primary", width="stretch"):
        try:
            package_is_demo = st.session_state.get("package_is_demo", True)
            client = None if package_is_demo else LLMClient()
            with st.status("正在更新 Blueprint…", expanded=True) as status:
                status.write("先更新 Course Blueprint")
                updated_package = RevisionService(client).revise_package(
                    blueprint, revision_request
                )
                status.write(
                    f"affected_ids：{', '.join(updated_package['revision']['affected_ids'])}"
                )
                status.write("重新生成受影响的教案与 PPT")
                status.write("再次检查一致性")
                updated_package["course_input"] = package.get("course_input", {})
                status.update(label="教学包已更新", state="complete", expanded=False)
            _save_package(updated_package, package_is_demo)
            st.success(updated_package["revision"]["change_summary"])
            st.rerun()
        except (ValidationError, ValueError, LLMConfigurationError, LLMGenerationError) as exc:
            st.error(f"更新失败：{exc}")
        except Exception as exc:
            st.exception(exc)

    st.subheader("4. 导出")
    try:
        pptx_bytes = export_slide_deck_pptx(blueprint, slide_deck)
        docx_bytes = export_lesson_plan_docx(blueprint, lesson_plan, slide_deck)
        json_bytes = json.dumps(package, ensure_ascii=False, indent=2).encode("utf-8")
        code_extension = {
            "Python": "py",
            "C++": "cpp",
            "Scratch": "txt",
        }[blueprint.course.language]
        comment = "//" if code_extension == "cpp" else "#"
        code_text = "\n\n".join(
            f"{comment} {item.id} · {item.title}\n{item.code}"
            for item in blueprint.code_examples
        ).encode("utf-8")
        base = safe_filename(blueprint.course.title)
        cols = st.columns(4)
        cols[0].download_button(
            "下载精简授课版教案",
            docx_bytes,
            file_name=f"{base}-精简授课版教案.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )
        cols[1].download_button(
            "下载课件 PPTX",
            pptx_bytes,
            file_name=f"{base}-课件.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            width="stretch",
        )
        cols[2].download_button(
            "下载完整 JSON",
            json_bytes,
            file_name=f"{base}-完整教学包.json",
            mime="application/json",
            width="stretch",
        )
        cols[3].download_button(
            "下载示例代码",
            code_text,
            file_name=f"{base}-示例代码.{code_extension}",
            mime="text/plain",
            width="stretch",
        )
    except Exception as exc:
        st.error(f"准备导出文件时失败：{exc}")
else:
    st.info("填写课程信息并点击“生成完整教学包”，结果将在这里显示。")

st.divider()
st.caption(
    "LessonCraft AI 是以课程内容生成和一致性控制为核心的轻量 AI Skill MVP，"
    "不是大型在线教育平台。"
)
