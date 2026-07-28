"""Generate full teaching packages from one canonical Blueprint."""

from __future__ import annotations

from typing import Any

from models.blueprint import CourseBlueprint
from models.course_input import CourseInput
from models.lesson_plan import LessonPlan, LessonPlanStage
from models.slide_deck import (
    CodeDisplay,
    Slide,
    SlideDeck,
    SlideInteraction,
    SourceRepair,
    SpeakerNotes,
    StepSlideBinding,
)
from prompts.blueprint_prompt import SYSTEM_PROMPT as BLUEPRINT_SYSTEM
from prompts.blueprint_prompt import build_user_prompt as blueprint_user_prompt
from prompts.lesson_plan_prompt import SYSTEM_PROMPT as LESSON_SYSTEM
from prompts.lesson_plan_prompt import build_user_prompt as lesson_user_prompt
from prompts.slide_deck_prompt import SYSTEM_PROMPT as SLIDE_SYSTEM
from prompts.slide_deck_prompt import build_user_prompt as slide_user_prompt
from prompts.consistency_prompt import SYSTEM_PROMPT as CONSISTENCY_SYSTEM
from prompts.consistency_prompt import build_user_prompt as consistency_user_prompt
from models.consistency import ConsistencyReport, ConsistencySummary

from .consistency_checker import ConsistencyChecker
from .llm_client import LLMClient


def _shorten(text: str, limit: int) -> str:
    """Keep generated navigation fields readable without cutting source IDs."""

    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"


def build_step_bindings(
    blueprint: CourseBlueprint, slide_deck: SlideDeck
) -> list[StepSlideBinding]:
    """Derive step-to-slide/activity/code mappings from the actual deck."""

    bindings: list[StepSlideBinding] = []
    for step in blueprint.lesson_flow:
        slides = [
            slide for slide in slide_deck.slides if step.id in slide.source_step_ids
        ]
        bindings.append(
            StepSlideBinding(
                step_id=step.id,
                slide_ids=[slide.id for slide in slides],
                activity_ids=list(
                    dict.fromkeys(
                        activity_id
                        for slide in slides
                        for activity_id in slide.activity_ids
                    )
                ),
                code_example_ids=list(
                    dict.fromkeys(
                        code_id
                        for slide in slides
                        for code_id in (
                            [slide.code_example_id] if slide.code_example_id else []
                        )
                    )
                ),
            )
        )
    return bindings


def normalize_slide_deck_sources(
    blueprint: CourseBlueprint, slide_deck: SlideDeck
) -> SlideDeck:
    """Repair illegal source IDs and retain an explicit audit record."""

    normalized = slide_deck.model_copy(deep=True)
    steps = {step.id: step for step in blueprint.lesson_flow}
    repairs = list(normalized.source_repairs)
    for slide in normalized.slides:
        source_steps = [
            steps[step_id] for step_id in slide.source_step_ids if step_id in steps
        ]
        allowed_objectives = {
            objective_id
            for step in source_steps
            for objective_id in step.objective_ids
        }
        allowed_knowledge = {
            knowledge_id
            for step in source_steps
            for knowledge_id in step.knowledge_ids
        }
        if source_steps:
            invalid_objectives = sorted(set(slide.objective_ids) - allowed_objectives)
            if invalid_objectives:
                slide.objective_ids = [
                    item for item in slide.objective_ids if item in allowed_objectives
                ]
                repairs.append(
                    SourceRepair(
                        slide_id=slide.id,
                        field="objective_ids",
                        removed_ids=invalid_objectives,
                        reason="Slide.objective_ids 必须是来源 STEP 目标的子集",
                    )
                )
            invalid_knowledge = sorted(set(slide.knowledge_ids) - allowed_knowledge)
            if invalid_knowledge:
                slide.knowledge_ids = [
                    item for item in slide.knowledge_ids if item in allowed_knowledge
                ]
                repairs.append(
                    SourceRepair(
                        slide_id=slide.id,
                        field="knowledge_ids",
                        removed_ids=invalid_knowledge,
                        reason="Slide.knowledge_ids 必须来自来源 STEP",
                    )
                )
    normalized.source_repairs = repairs
    normalized.step_bindings = build_step_bindings(blueprint, normalized)
    return normalized


def sync_lesson_slide_ids(
    lesson_plan: LessonPlan,
    slide_deck: SlideDeck,
    blueprint: CourseBlueprint | None = None,
) -> LessonPlan:
    """Bind lesson stages to actual slides and optionally canonical execution data."""

    synced = lesson_plan.model_copy(deep=True)
    steps = {step.id: step for step in blueprint.lesson_flow} if blueprint else {}
    bindings = {item.step_id: item for item in slide_deck.step_bindings}
    for stage in synced.stages:
        stage.slide_ids = [
            slide.id for slide in slide_deck.slides if stage.step_id in slide.source_step_ids
        ]
        source = steps.get(stage.step_id)
        binding = bindings.get(stage.step_id)
        if binding is not None:
            stage.materials_or_code = [
                *binding.activity_ids,
                *binding.code_example_ids,
            ][:6]
        if source is not None:
            stage.duration_minutes = source.duration_minutes
            stage.duration = source.duration.model_copy(deep=True)
            stage.objective_ids = list(source.objective_ids)
            stage.knowledge_ids = list(source.knowledge_ids)
            stage.student_action = (
                source.student_action.model_copy(deep=True)
                if source.student_action
                else None
            )
            if source.student_action:
                stage.student_activity = source.student_action.action
    return synced


def derive_lesson_plan(
    blueprint: CourseBlueprint, slide_deck: SlideDeck | None = None
) -> LessonPlan:
    """Create a deterministic concise teaching plan for Demo Mode and revisions."""

    deck = slide_deck or derive_slide_deck(blueprint)
    slide_map = {
        step.id: [
            slide.id for slide in deck.slides if step.id in slide.source_step_ids
        ]
        for step in blueprint.lesson_flow
    }
    binding_map = {
        item.step_id: item for item in build_step_bindings(blueprint, deck)
    }
    objectives = {item.id: item for item in blueprint.learning_objectives}
    stages = [
        LessonPlanStage(
            step_id=step.id,
            title=step.title,
            duration_minutes=step.duration_minutes,
            duration=step.duration.model_copy(deep=True),
            objective_ids=step.objective_ids,
            knowledge_ids=step.knowledge_ids,
            teacher_activity=_shorten(step.teacher_activity, 150),
            student_activity=_shorten(
                step.student_action.action
                if step.student_action
                else step.student_activity,
                150,
            ),
            student_action=(
                step.student_action.model_copy(deep=True)
                if step.student_action
                else None
            ),
            key_question=_shorten(step.key_question, 100),
            assessment=_shorten(
                "；".join(
                    objectives[item_id].assessment
                    for item_id in step.objective_ids
                    if item_id in objectives
                ),
                160,
            ),
            slide_ids=slide_map.get(step.id, []),
            materials_or_code=(
                [
                    *binding_map[step.id].activity_ids,
                    *binding_map[step.id].code_example_ids,
                ][:6]
                if step.id in binding_map
                else []
            ),
        )
        for step in blueprint.lesson_flow
    ]
    return LessonPlan(
        plan_type="concise",
        course_overview=(
            f"面向 {blueprint.course.age_range} 学生的 {blueprint.course.duration_minutes} 分钟"
            f"{blueprint.course.language}课程；核心任务：{blueprint.course.core_goal}。"
        ),
        teaching_objectives=[item.content for item in blueprint.learning_objectives],
        key_points=[
            _shorten(f"{item.name}：{item.definition}", 90)
            for item in blueprint.knowledge_points
        ],
        difficult_points=[
            _shorten(error, 70)
            for item in blueprint.knowledge_points
            for error in item.common_errors[:1]
        ],
        preparation=[
            f"可运行 {blueprint.course.language} 的教学环境",
            "投影设备与学生练习文件",
            "提前验证 Blueprint 中的示例代码",
        ],
        stages=stages,
        classroom_assessment=[item.assessment for item in blueprint.learning_objectives],
        homework=[
            item.question
            for item in blueprint.exercises
            if item.delivery_mode in {"student_assignment", "extension_challenge"}
        ][:2]
        or ["在课堂作品基础上增加一次输入校验，并说明修改原因。"],
        teacher_reminders=[
            "先让学生预测结果，再运行代码验证。",
            "只使用 Blueprint 中定义的术语与示例代码。",
            "教案时间含讲解、学生操作、巡视和过渡；PPT 备注仅表示投屏讲解时间。",
            "关注过程性提问，不以完成速度作为唯一评价标准。",
        ],
        code_example_ids=[item.id for item in blueprint.code_examples],
    )


def _at(items: list[Any], index: int) -> Any:
    """Safely select a classroom step from a short Blueprint."""

    return items[min(index, len(items) - 1)]


def _fit_slide_times_to_step_budgets(
    blueprint: CourseBlueprint, slides: list[Slide]
) -> None:
    """Scale per-page explanation times to the current STEP presentation budget."""

    for step in blueprint.lesson_flow:
        step_slides = [
            slide for slide in slides if step.id in slide.source_step_ids
        ]
        if not step_slides:
            continue
        budget = step.duration.presentation_minutes
        if budget < len(step_slides):
            raise ValueError(
                f"{step.id} 的 presentation_minutes 不足以给每页至少 1 分钟"
            )
        current = [slide.speaker_notes.suggested_minutes for slide in step_slides]
        current_total = sum(current)
        allocated = [
            max(1, round(value * budget / current_total)) for value in current
        ]
        difference = budget - sum(allocated)
        cursor = 0
        while difference:
            index = cursor % len(allocated)
            if difference > 0:
                allocated[index] += 1
                difference -= 1
            elif allocated[index] > 1:
                allocated[index] -= 1
                difference += 1
            cursor += 1
        for slide, minutes in zip(step_slides, allocated, strict=True):
            slide.speaker_notes.suggested_minutes = minutes


def derive_slide_deck(blueprint: CourseBlueprint) -> SlideDeck:
    """Create a paced classroom deck without inventing Blueprint knowledge."""

    steps = blueprint.lesson_flow
    objectives = [item.id for item in blueprint.learning_objectives]
    knowledge_ids = [item.id for item in blueprint.knowledge_points]
    terms = blueprint.terminology
    first_code = blueprint.code_examples[0] if blueprint.code_examples else None
    project_code = (
        blueprint.code_examples[-1] if blueprint.code_examples else None
    )
    first, concept, code_step, practice, project, close = (
        _at(steps, 0),
        _at(steps, 1),
        _at(steps, 2),
        _at(steps, 3),
        _at(steps, 4),
        _at(steps, 5),
    )
    activities_by_step = {
        step.id: [
            item for item in blueprint.activities if step.id in item.step_ids
        ]
        for step in steps
    }

    def notes(
        explanation: str,
        question: str = "",
        demo: str = "",
        warning: str = "",
        minutes: int = 2,
        transition: str = "带着刚才的发现进入下一页。",
    ) -> SpeakerNotes:
        return SpeakerNotes(
            explanation=_shorten(explanation, 170),
            question=_shorten(question, 115),
            demo=_shorten(demo, 145),
            warning=_shorten(warning, 115),
            suggested_minutes=minutes,
            transition=_shorten(transition, 115),
        )

    slides: list[Slide] = []

    def add(**kwargs: Any) -> None:
        slides.append(Slide(id=f"SLIDE-{len(slides) + 1:02d}", **kwargs))

    add(
        title=blueprint.course.title,
        layout="title",
        slide_type="cover",
        learning_action="observe",
        visual_direction="深色封面，只保留课程挑战与完成目标。",
        content=[
            f"{blueprint.course.language} · {blueprint.course.age_range}",
            blueprint.course.core_goal,
        ],
        speaker_notes=notes(
            "用最终作品建立期待，不展开知识定义。",
            "今天这个程序需要解决什么问题？",
            minutes=1,
            transition="先体验一次只允许猜一次的版本。",
        ),
    )
    add(
        title=first.title,
        layout="question",
        slide_type="scenario",
        learning_action="discuss",
        visual_direction="中央大问题，底部保留同伴讨论提示。",
        content=["第一次猜错后，游戏结束了。", "我们希望玩家可以继续猜。"],
        source_step_ids=[first.id],
        objective_ids=first.objective_ids,
        interaction=SlideInteraction(
            type="question",
            prompt=first.key_question,
            expected_response="让程序回到输入位置并再次判断。",
        ),
        speaker_notes=notes(
            "只描述体验冲突，让学生先提出“重复”的需求。",
            first.key_question,
            "运行一次只能猜一次的版本。",
            minutes=3,
            transition="把学生的想法整理成今天的课程挑战。",
        ),
    )
    add(
        title="今天的挑战：猜中前一直继续",
        layout="section",
        slide_type="challenge",
        learning_action="observe",
        visual_direction="用一句挑战目标和三项完成标准形成章节页。",
        content=[
            "允许重复输入",
            "每次给出大小提示",
            "猜中后停止并祝贺",
        ],
        source_step_ids=[first.id],
        objective_ids=first.objective_ids,
        speaker_notes=notes(
            "把学习目标改写成学生能判断是否完成的作品标准。",
            "完成后你会用哪三种输入测试游戏？",
            minutes=2,
            transition="先找出我们已经会用的工具。",
        ),
    )
    add(
        title="旧工具够用吗？",
        layout="comparison",
        slide_type="review",
        learning_action="recall",
        visual_direction="左右对比：已有工具与尚未解决的问题。",
        content=["变量：保存答案", "input：读取猜测", "if：判断一次", "缺少：重复判断"],
        source_step_ids=[first.id],
        objective_ids=first.objective_ids,
        interaction=SlideInteraction(
            type="choice",
            prompt="哪一个工具只能判断一次，不能让游戏继续？",
            expected_response="if 只能完成一次条件判断。",
        ),
        speaker_notes=notes(
            "快速激活变量、input 和 if，不重新讲授旧知识。",
            "哪一个工具只能判断一次？",
            warning="不要把旧知识回顾扩展成新课。",
            minutes=3,
            transition="接下来认识负责“重复”的新工具。",
        ),
    )
    add(
        title=f"{terms[0].term}：条件为真就继续",
        layout="concept",
        slide_type="concept",
        learning_action="explain",
        visual_direction="左侧标准定义，右侧 True/False 两种去向。",
        content=[
            _shorten(terms[0].standard_definition, 70),
            "条件为 True：执行并再次判断",
            "条件为 False：离开循环",
        ],
        source_step_ids=[concept.id],
        objective_ids=concept.objective_ids,
        knowledge_ids=concept.knowledge_ids,
        speaker_notes=notes(
            "强调每轮开始前都会重新判断条件。",
            "条件变成 False 后，程序去哪里？",
            warning="避免把 while 说成固定重复次数。",
            minutes=4,
            transition="用一个流程把判断和重复连接起来。",
        ),
    )
    add(
        title="先判断，再执行，再回去",
        layout="concept",
        slide_type="process",
        learning_action="predict",
        visual_direction="三步水平流程：判断条件、执行代码、回到判断。",
        content=["判断循环条件", "执行缩进代码", "回到条件再次判断"],
        source_step_ids=[concept.id],
        objective_ids=concept.objective_ids,
        knowledge_ids=concept.knowledge_ids,
        interaction=SlideInteraction(
            type="prediction",
            prompt="如果条件连续三次都是 True，循环体会执行几次？",
            expected_response="执行三次，然后还要继续判断下一次条件。",
        ),
        speaker_notes=notes(
            "沿流程指读一遍，重点是执行后会回到条件。",
            "连续三次 True 会执行几次？",
            "用手指沿三步流程走一圈。",
            minutes=3,
            transition="把流程变成一个全班可参与的循环。",
        ),
    )
    activity = (
        activities_by_step.get(concept.id, [None])[0]
        if activities_by_step.get(concept.id)
        else None
    )
    add(
        title=activity.title if activity else "人体 while 循环",
        layout="activity",
        slide_type="interaction",
        learning_action="practice",
        visual_direction="突出动作指令与停止条件，减少解释文字。",
        content=[
            _shorten(activity.instructions, 80)
            if activity
            else _shorten(concept.student_activity, 80),
            "观察：条件什么时候改变？",
            "目标：能说出循环何时停止",
        ],
        source_step_ids=[concept.id],
        objective_ids=concept.objective_ids,
        knowledge_ids=concept.knowledge_ids,
        activity_ids=[activity.id] if activity else [],
        interaction=SlideInteraction(
            type="hands_on",
            prompt="按条件牌行动；条件变为 False 时立即停下。",
            expected_response="学生能在条件变化时停止动作并说明原因。",
        ),
        speaker_notes=notes(
            "先宣布规则，再开始动作；结束后追问停止原因。",
            "你为什么在这一轮停下？",
            "请两名学生分别扮演条件与循环体。",
            minutes=5,
            transition="现在把刚才的动作规则写成最小代码。",
        ),
    )
    if first_code:
        code_activity = (
            activities_by_step.get(code_step.id, [None])[0]
            if activities_by_step.get(code_step.id)
            else None
        )
        add(
            title="最小代码：重复输入直到猜中",
            layout="code",
            slide_type="code_minimal",
            learning_action="code",
            visual_direction="代码占主区域，只解释循环条件与输入更新。",
            content=["条件：guess != answer", "每轮更新 guess", "猜中后离开循环"],
            source_step_ids=[code_step.id],
            objective_ids=first_code.objective_ids,
            knowledge_ids=first_code.knowledge_ids,
            code_example_id=first_code.id,
            activity_ids=[code_activity.id] if code_activity else [],
            code_display=CodeDisplay(
                code_example_id=first_code.id,
                highlight_lines=[4, 5],
                reveal_step=1,
            ),
            speaker_notes=notes(
                first_code.explanation,
                "哪一行让条件有机会变成 False？",
                f"逐行运行 {first_code.id}，观察 guess 的变化。",
                "input 必须位于循环体内。",
                minutes=5,
                transition="先不运行，预测不同输入会走几轮。",
            ),
        )
        add(
            title="运行前先预测",
            layout="code",
            slide_type="prediction",
            learning_action="predict",
            visual_direction="保留同一代码，突出循环条件并放大预测问题。",
            content=["输入 3 → True", "输入 7 → False", "输出：猜对了"],
            source_step_ids=[code_step.id],
            objective_ids=first_code.objective_ids,
            knowledge_ids=first_code.knowledge_ids,
            code_example_id=first_code.id,
            activity_ids=[code_activity.id] if code_activity else [],
            code_display=CodeDisplay(
                code_example_id=first_code.id,
                highlight_lines=[4, 5, 7],
                reveal_step=2,
            ),
            interaction=SlideInteraction(
                type="prediction",
                prompt="依次输入 3、7，循环体一共执行几次？",
                expected_response="执行两次；第二次输入后条件变为 False。",
            ),
            speaker_notes=notes(
                "先收集预测，再运行验证；不要直接公布答案。",
                "输入 3、7 时循环执行几次？",
                "用两次输入运行同一份 Blueprint 代码。",
                minutes=4,
                transition="最小循环能停止了，下一步加入大小提示。",
            ),
        )
    add(
        title=practice.title,
        layout="activity",
        slide_type="activity",
        learning_action="practice",
        visual_direction="任务置顶，下面给出三步完成路径。",
        content=[
            "把 if / elif 放进循环体",
            "每次输入后给出大小提示",
            "用偏小、偏大、正确三类输入测试",
        ],
        source_step_ids=[practice.id],
        objective_ids=practice.objective_ids,
        knowledge_ids=practice.knowledge_ids,
        interaction=SlideInteraction(
            type="fill_blank",
            prompt="大小判断应该放在 while 的里面还是外面？",
            expected_response="放在循环体内，才能每轮都给反馈。",
        ),
        speaker_notes=notes(
            "先明确成功标准，再让学生补全半成品。",
            "大小判断应该放在哪里？",
            "展示缩进位置，不提供新的代码版本。",
            "常见错误是判断放到循环外。",
            minutes=8,
            transition="动手前先诊断两种最常见的错误。",
        ),
    )
    errors = [
        error
        for item in blueprint.knowledge_points
        for error in item.common_errors
    ][:3]
    add(
        title="调试挑战：为什么它停不下来？",
        layout="question",
        slide_type="error",
        learning_action="debug",
        visual_direction="错误现象居中，底部列出检查顺序。",
        content=errors or ["检查条件", "检查输入位置", "检查循环变量是否更新"],
        source_step_ids=[practice.id],
        objective_ids=practice.objective_ids,
        knowledge_ids=practice.knowledge_ids,
        interaction=SlideInteraction(
            type="debug",
            prompt="先检查哪一项：条件、缩进，还是变量更新？",
            expected_response="按条件—缩进—变量更新的顺序逐项检查。",
        ),
        speaker_notes=notes(
            "让学生说出诊断顺序，不直接替学生修改代码。",
            "循环不停止时先看哪里？",
            "演示手动终止后再定位错误。",
            "不要运行无法安全终止的死循环太久。",
            minutes=4,
            transition="带着调试清单完成完整项目。",
        ),
    )
    if project_code:
        add(
            title=project_code.title,
            layout="code",
            slide_type="project",
            learning_action="create",
            visual_direction="完整代码置左，右侧列作品验收标准。",
            content=["循环读取输入", "if / elif 给出反馈", "猜中后退出并祝贺"],
            source_step_ids=[project.id],
            objective_ids=project_code.objective_ids,
            knowledge_ids=project_code.knowledge_ids,
            code_example_id=project_code.id,
            code_display=CodeDisplay(
                code_example_id=project_code.id,
                highlight_lines=[4, 5, 6, 8],
                reveal_step=3,
            ),
            speaker_notes=notes(
                project_code.explanation,
                "这份完整代码怎样满足三个作品标准？",
                f"运行 {project_code.id} 的三类测试输入。",
                "保持 Blueprint 原始代码，不现场改写另一个版本。",
                minutes=5,
                transition="接下来由学生独立完成并互相测试。",
            ),
        )
    project_activity = (
        activities_by_step.get(project.id, [None])[0]
        if activities_by_step.get(project.id)
        else None
    )
    add(
        title="学生动手：完成并测试游戏",
        layout="assignment",
        slide_type="activity",
        learning_action="create",
        visual_direction="左侧任务，右侧三项完成检查。",
        content=[
            _shorten(
                project_activity.instructions
                if project_activity
                else project.student_activity,
                80,
            ),
            "测试偏小输入",
            "测试偏大输入",
            "测试正确输入",
        ],
        source_step_ids=[project.id],
        objective_ids=project.objective_ids,
        knowledge_ids=project.knowledge_ids,
        activity_ids=[project_activity.id] if project_activity else [],
        interaction=SlideInteraction(
            type="hands_on",
            prompt="完成后与同伴交换测试，并记录一个发现。",
            expected_response="作品通过三类输入测试，学生能说明停止条件。",
        ),
        speaker_notes=notes(
            "用完成标准巡视，不逐行替学生写代码。",
            "你用什么证据证明游戏能正确停止？",
            "请同伴输入三类测试数据。",
            minutes=2,
            transition="用测试证据回到本课核心结论。",
        ),
    )
    add(
        title="记住这三件事",
        layout="summary",
        slide_type="summary",
        learning_action="reflect",
        visual_direction="三条核心结论分层呈现，突出 True 与 False。",
        content=[
            _shorten(item.standard_definition, 75) for item in terms[:3]
        ],
        source_step_ids=[close.id],
        objective_ids=objectives,
        knowledge_ids=knowledge_ids,
        interaction=SlideInteraction(
            type="reflection",
            prompt="用一句话说明 while 循环何时继续、何时停止。",
            expected_response="条件为 True 时继续，条件为 False 时停止。",
        ),
        speaker_notes=notes(
            "先让学生复述，再显示标准术语。",
            "while 循环何时继续、何时停止？",
            warning="不要把总结变成重新讲一遍整节课。",
            minutes=4,
            transition="最后选择一个挑战继续升级作品。",
        ),
    )
    challenge_exercise = next(
        (
            item
            for item in blueprint.exercises
            if item.display_on_slide
            and item.delivery_mode
            in {"student_assignment", "extension_challenge"}
        ),
        blueprint.exercises[-1] if blueprint.exercises else None,
    )
    challenge = (
        challenge_exercise.question
        if challenge_exercise
        else "为作品增加一次升级。"
    )
    add(
        title="课后挑战：让游戏更完整",
        layout="assignment",
        slide_type="assignment",
        learning_action="create",
        visual_direction="大任务 + 两条验收标准，不展示答案。",
        content=[_shorten(challenge, 90), "保留原有功能", "说明你新增了什么"],
        source_step_ids=[close.id],
        objective_ids=close.objective_ids,
        knowledge_ids=close.knowledge_ids,
        exercise_ids=[challenge_exercise.id] if challenge_exercise else [],
        speaker_notes=notes(
            "只说明任务和验收标准，不在课堂末尾给出完整答案。",
            "你准备先修改哪一部分？",
            minutes=2,
            transition="课程结束，保存作品与测试记录。",
        ),
    )

    if len(slides) > blueprint.course.max_slides:
        # Demo defaults to 15 pages. For lower caps, keep the strongest classroom spine.
        keep_indices = {
            0,
            1,
            2,
            4,
            5,
            7,
            8,
            9,
            10,
            11,
            12,
            len(slides) - 2,
            len(slides) - 1,
        }
        priority = [slide for index, slide in enumerate(slides) if index in keep_indices]
        optional = [slide for index, slide in enumerate(slides) if index not in keep_indices]
        slides = (priority + optional)[: blueprint.course.max_slides]
        order = {step.id: index for index, step in enumerate(steps)}
        slides[1:] = sorted(
            slides[1:],
            key=lambda slide: min(
                (order[item] for item in slide.source_step_ids if item in order),
                default=-1,
            ),
        )
    for index, slide in enumerate(slides, start=1):
        slide.id = f"SLIDE-{index:02d}"
    _fit_slide_times_to_step_budgets(blueprint, slides)
    deck = SlideDeck(title=blueprint.course.title, slides=slides)
    deck.step_bindings = build_step_bindings(blueprint, deck)
    return deck


class CourseGenerator:
    """Orchestrate Blueprint-first generation using one compatible LLM client."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate_blueprint(self, course_input: CourseInput) -> CourseBlueprint:
        """Generate and validate the single source of truth."""

        data = self.llm_client.generate_json(
            BLUEPRINT_SYSTEM, blueprint_user_prompt(course_input)
        )
        return CourseBlueprint.model_validate(data)

    def generate_lesson_plan(self, blueprint: CourseBlueprint) -> LessonPlan:
        """Generate a plan using only the validated Blueprint."""

        data = self.llm_client.generate_json(LESSON_SYSTEM, lesson_user_prompt(blueprint))
        return LessonPlan.model_validate(data)

    def generate_slide_deck(self, blueprint: CourseBlueprint) -> SlideDeck:
        """Generate a bounded slide deck using only the validated Blueprint."""

        data = self.llm_client.generate_json(SLIDE_SYSTEM, slide_user_prompt(blueprint))
        deck = SlideDeck.model_validate(data)
        if len(deck.slides) > blueprint.course.max_slides:
            raise ValueError(
                f"PPT 共 {len(deck.slides)} 页，超过上限 {blueprint.course.max_slides} 页"
            )
        return normalize_slide_deck_sources(blueprint, deck)

    def generate_consistency_report(
        self,
        blueprint: CourseBlueprint,
        lesson_plan: LessonPlan,
        slide_deck: SlideDeck,
    ) -> ConsistencyReport:
        """Combine deterministic hard checks with a read-only semantic review."""

        local_report = ConsistencyChecker().check(blueprint, lesson_plan, slide_deck)
        if local_report.status == "fail":
            return local_report
        semantic_data = self.llm_client.generate_json(
            CONSISTENCY_SYSTEM,
            consistency_user_prompt(blueprint, lesson_plan, slide_deck),
        )
        semantic_report = ConsistencyReport.model_validate(semantic_data)
        semantic_checks = []
        local_names = {item.name for item in local_report.checks}
        for item in semantic_report.checks:
            if item.name in local_names:
                item.name = f"semantic_{item.name}"
            semantic_checks.append(item)
        blocking = [*local_report.blocking_issues, *semantic_report.blocking_issues]
        warnings = [*local_report.warnings, *semantic_report.warnings]
        status = "fail" if blocking or semantic_report.status == "fail" else (
            "warning"
            if warnings or semantic_report.status == "warning"
            else "pass"
        )
        checks = [*local_report.checks, *semantic_checks]

        def scope_status(scope: str) -> str:
            scoped = [item for item in checks if item.scope == scope]
            if any(item.status == "fail" for item in scoped):
                return "fail"
            if any(item.status == "warning" for item in scoped):
                return "warning"
            return "pass"

        return ConsistencyReport(
            status=status,
            checks=checks,
            blocking_issues=blocking,
            warnings=warnings,
            summary=ConsistencySummary(
                core_fact_status=scope_status("core"),
                execution_alignment_status=scope_status("execution"),
                passed_checks=sum(item.status == "pass" for item in checks),
                warning_checks=sum(item.status == "warning" for item in checks),
                failed_checks=sum(item.status == "fail" for item in checks),
            ),
        )

    def generate_package(self, course_input: CourseInput) -> dict[str, Any]:
        """Generate every artifact and finish with deterministic checks."""

        blueprint = self.generate_blueprint(course_input)
        lesson_plan = self.generate_lesson_plan(blueprint)
        slide_deck = self.generate_slide_deck(blueprint)
        lesson_plan = sync_lesson_slide_ids(lesson_plan, slide_deck, blueprint)
        report = self.generate_consistency_report(blueprint, lesson_plan, slide_deck)
        return {
            "course_input": course_input.model_dump(mode="json"),
            "blueprint": blueprint.model_dump(mode="json"),
            "lesson_plan": lesson_plan.model_dump(mode="json"),
            "slide_deck": slide_deck.model_dump(mode="json"),
            "consistency_report": report.model_dump(mode="json"),
        }
