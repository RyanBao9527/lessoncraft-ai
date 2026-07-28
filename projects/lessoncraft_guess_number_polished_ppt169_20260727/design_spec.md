<!-- ppt-master-schema: design-spec/v1 -->
# LessonCraft Guess Number Polished - Design Spec

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | LessonCraft Guess Number Polished |
| Canvas Format | PPT 16:9, 1280 × 720 |
| Page Count | 15 |
| Target Audience | 10～12 岁、学过变量、input 和 if 的少儿 Python 学生。 |
| Communication Intent | 用于教师现场投屏授课；以问题、预测、代码观察和动手任务推动学生理解 while 循环并完成猜数字游戏。 |
| Desired Audience Outcome | 学生能判断 while 循环何时继续和停止，读懂两段冻结代码，并按课堂任务完成、测试猜数字游戏。 |
| Core Message / Ask / Action | while 在条件为 True 时继续执行；通过更新 guess，让游戏在猜中时停止。 |
| Delivery Context | 主要用于有教师讲解的教室投屏；次要用于教师课前预览和课后复用。 |
| Artifact Afterlife | 保留为原生可编辑 PPTX，供教师继续修改、复用和归档。 |
| Reading Mode | presentation |
| Content Strategy | 保持源 PPT 的全部文字、代码、页数、页序和逐页教学含义逐字不变，只重新设计视觉布局。 |
| Design Style | instructional mode + soft-rounded visual style；明亮游戏课堂，以深海蓝、奖励黄、清新绿构成统一课堂游戏 UI。 |
| Formula Policy | text-only |
| AI Image Acquisition Path | not applicable |
| Generation Mode | continuous |
| Spec Refinement | disabled |
| Created Date | 2026-07-27 |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| Format | PPT 16:9 |
| Dimensions | 1280 × 720 |
| viewBox | `0 0 1280 720` |
| Margins | 40 px minimum safe margin; 48 px preferred for titles and primary content |
| Content Area | x=48–1232, y=40–680; footer labels remain inside y=672–700 |

## III. Visual Theme

### Theme Style

- **Mode**: instructional
- **Visual style**: soft-rounded
- **Theme**: 明亮编程游戏课堂；圆角任务面板、状态徽章、游戏进度暗示、高对比代码控制台。
- **Tone**: 活泼但不幼稚，科技感与游戏感适量，教室投屏清晰优先。

### Color Scheme

| Role | HEX | Purpose |
| --- | --- | --- |
| Background | #F7FBFF | 主体明亮背景与大面积留白 |
| Secondary background | #DCEEFA | 信息卡、流程区、浅色问题区 |
| Primary | #18314E | 标题、深色主卡、代码页之外的强层级 |
| Accent | #FFC444 | 行动提示、预测条、关卡奖励与代码高亮 |
| Secondary accent | #2B8F67 | 正确状态、步骤、运行与完成提示 |
| Body text | #232931 | 正文与说明文字 |

## IV. Typography System

### Font Plan

| Role | Chinese | English | Fallback tail |
| --- | --- | --- | --- |
| Title | Microsoft YaHei | Arial | PingFang SC, sans-serif |
| Body | Microsoft YaHei | Arial | PingFang SC, sans-serif |
| Code | Microsoft YaHei | Menlo | Consolas, Courier New, monospace |

- **Title stack**: "Microsoft YaHei", "PingFang SC", Arial, sans-serif
- **Body stack**: "Microsoft YaHei", "PingFang SC", Arial, sans-serif
- **Code stack**: Menlo, Consolas, "Courier New", "Microsoft YaHei", monospace
- **Role rationale**: Python 代码使用独立等宽字体；中文字符串通过中文后备字体保持可读与不乱码。

### Font Size Hierarchy

| Purpose | Anchor Size (px) |
| --- | ---: |
| Body | 32 |
| Title | 56 |
| Subtitle | 44 |
| Annotation | 24 |
| Code | 22 |

## V. Layout Principles

### Page Structure

- **Header area**: 内容页使用左对齐标题与短状态标签；问题页允许核心问题占据标题以下的主视觉区。
- **Content area**: 根据页面语义使用问题焦点、目标卡、流程链、代码控制台、任务卡、总结节点等不同构图；不重复单一项目符号版式。
- **Footer area**: 保留所有源文件中的 `LessonCraft AI · STEP-*` 与 `SLIDE-*` 文字，降低对比但不删除。

### Spacing Specification

| Element | Current Project |
| --- | --- |
| Safe margin | 40–48 px |
| Content block gap | 20–28 px |
| Icon-text gap | 10–14 px |

## VI. Icon Usage Specification

- **Primary bundled library**: tabler-filled

| Purpose | Icon Path | Page |
| --- | --- | --- |
| 问题与预测状态 | tabler-filled/help-circle, tabler-filled/bulb | P02, P06, P09, P11 |
| 代码与调试状态 | tabler-filled/file-code, tabler-filled/bug | P08, P09, P11, P12 |
| 动手任务与完成检查 | tabler-filled/device-gamepad-2, tabler-filled/check | P07, P10, P13, P15 |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Crop Policy | Acquire Via | Status | Reference | text_policy | page_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## IX. Content Outline

### Part 1: 课程挑战与旧知识

#### Slide 01 - Python 猜数字游戏：用 while 让游戏继续

- **Audience move**: 从尚未进入课堂情境 → 期待完成一个能持续猜测的 Python 小游戏。
- **Layout**: 游戏启动封面；深色圆角主舞台、原生可编辑像素格与状态条，课程题目居中，保留大量投屏留白。
- **Title**: Python 猜数字游戏：用 while 让游戏继续
- **Core message**: 本课将用 while 让猜数字游戏持续运行。
- **Content**: 逐字呈现 `Python 猜数字游戏：用 while 让游戏继续`；`Python · 10～12 岁理解并使用 while 循环`；`从问题出发 · 用代码验证 · 完成作品`。

#### Slide 02 - 情境导入：一次没猜中怎么办

- **Audience move**: 从看到“一次猜错就结束”的现象 → 主动提出程序需要重复输入。
- **Layout**: 单一核心问题占主视觉区，两个现象说明作为轻量提示卡；问号与问题框突出，不增加其他教学文字。
- **Title**: 情境导入：一次没猜中怎么办
- **Core message**: 一次猜错不应结束游戏，程序需要回到输入位置。
- **Content**: 逐字呈现 `情境导入：一次没猜中怎么办`；`?`；`如果第一次没猜中，程序怎样回到输入的位置？`；`●  第一次猜错后，游戏结束了。`；`●  我们希望玩家可以继续猜。`；`LessonCraft AI · STEP-01`；`SLIDE-02`。

#### Slide 03 - 今天的挑战：猜中前一直继续

- **Audience move**: 从模糊的“继续猜”需求 → 理解三个可观察的作品完成标准。
- **Layout**: 关卡目标页；一个主挑战标题配三个等权目标卡，使用 01/02/03 作为关卡编号。
- **Title**: 今天的挑战：猜中前一直继续
- **Core message**: 游戏要能重复输入、给出提示并在猜中后停止。
- **Content**: 逐字呈现 `COURSE CHALLENGE`；`今天的挑战：猜中前一直继续`；`01`；`02`；`03`；`允许重复输入`；`每次给出大小提示`；`猜中后停止并祝贺`；`SLIDE-03`。

#### Slide 04 - 旧工具够用吗？

- **Audience move**: 从回忆变量、input、if → 识别旧工具缺少“重复判断”能力。
- **Layout**: 左右对比卡；“已经会用”与“还需解决”并列，底部保留黄色选择行动条。
- **Title**: 旧工具够用吗？
- **Core message**: 变量、input 和 if 能完成一次判断，但不能让游戏持续。
- **Content**: 逐字呈现 `旧工具够用吗？`；`已经会用`；`还需解决`；`●  变量：保存答案`；`●  input：读取猜测`；`●  if：判断一次`；`●  缺少：重复判断`；`哪一个工具只能判断一次，不能让游戏继续？`；`选一选`；`LessonCraft AI · STEP-01`；`SLIDE-04`。

### Part 2: while 概念与循环流程

#### Slide 05 - while 循环：条件为真就继续

- **Audience move**: 从知道“需要重复” → 理解 while 由条件 True/False 控制继续与停止。
- **Layout**: 一张深色概念定义主卡配右侧 True/False 状态分支；箭头和状态点辅助理解。
- **Title**: while 循环：条件为真就继续
- **Core message**: 条件为 True 时重复执行，False 时离开循环。
- **Content**: 逐字呈现 `while 循环：条件为真就继续`；`●  条件为 True：执行并再次判断`；`●  条件为 False：离开循环`；`while 循环会在条件为 True 时重复执行一组代码。`；`LessonCraft AI · STEP-02`；`SLIDE-05`。

#### Slide 06 - 先判断，再执行，再回去

- **Audience move**: 从理解条件控制 → 能沿三步流程预测循环执行次数。
- **Layout**: 三节点循环流程链，1/2/3 节点由箭头连接，底部预测行动条醒目。
- **Title**: 先判断，再执行，再回去
- **Core message**: 每轮先判断条件，再执行缩进代码，最后回到条件重新判断。
- **Content**: 逐字呈现 `先判断，再执行，再回去`；`1`；`2`；`3`；`判断循环条件`；`执行缩进代码`；`回到条件再次判断`；`→`；`→`；`如果条件连续三次都是 True，循环体会执行几次？`；`先预测`；`LessonCraft AI · STEP-02`；`SLIDE-06`。

#### Slide 07 - 人体 while 循环

- **Audience move**: 从抽象流程 → 通过身体动作体验条件变化与循环停止。
- **Layout**: 左侧橙色 DO 行动卡，右侧三个编号步骤；行动指令最大，观察问题与目标次级。
- **Title**: 人体 while 循环
- **Core message**: 条件为 True 就重复行动，False 时立即停止。
- **Content**: 逐字呈现 `人体 while 循环`；`一名学生举条件牌，另一名学生在条件为 True 时重复走一步，直到到达终点。`；`1`；`DO`；`观察：条件什么时候改变？`；`2`；`按条件牌行动；条件变为 False 时立即停下。`；`目标：能说出循环何时停止`；`3`；`LessonCraft AI · STEP-02`；`SLIDE-07`。

### Part 3: 最小代码与运行预测

#### Slide 08 - 最小代码：重复输入直到猜中

- **Audience move**: 从人体循环 → 能定位代码中的 while 条件与 guess 更新行。
- **Layout**: 高对比深色代码控制台占页面约 70%，右侧为三条代码观察卡；代码逐行呈现、等宽、不自动换行。
- **Title**: 最小代码：重复输入直到猜中
- **Core message**: 更新 guess 让循环条件最终变为 False。
- **Content**: 逐字呈现标题；以下代码块逐字符保持不变：

```text
 1  answer = 7
 2  guess = 0
 3  
 4  while guess != answer:
 5      guess = int(input("请输入 1～10 的数字："))
 6  
 7  print("猜对了！")
```

  逐字呈现 `代码来源` 与 `CODE-01`；`●  条件：guess != answer`；`●  每轮更新 guess`；`●  猜中后离开循环`；`LessonCraft AI · STEP-03`；`SLIDE-08`。

#### Slide 09 - 运行前先预测

- **Audience move**: 从阅读代码 → 在运行前预测输入 3、7 时的循环行为。
- **Layout**: 与 P08 保持同一代码控制台骨架，增加底部黄色预测条和右侧状态轨迹。
- **Title**: 运行前先预测
- **Core message**: 先预测条件变化，再运行验证。
- **Content**: 逐字呈现标题；以下代码块逐字符保持不变：

```text
 1  answer = 7
 2  guess = 0
 3  
 4  while guess != answer:
 5      guess = int(input("请输入 1～10 的数字："))
 6  
 7  print("猜对了！")
```

  逐字呈现 `代码来源` 与 `CODE-01`；`●  输入 3 → True`；`●  输入 7 → False`；`●  输出：猜对了`；`依次输入 3、7，循环体一共执行几次？`；`先预测`；`LessonCraft AI · STEP-03`；`SLIDE-09`。

### Part 4: 互动实践与调试

#### Slide 10 - 互动实践：加入大小提示

- **Audience move**: 从最小循环 → 知道大小判断需要放入循环体并用三类输入测试。
- **Layout**: 左侧 DO 任务卡，右侧三步任务链；核心位置问题作为橙色行动标题。
- **Title**: 互动实践：加入大小提示
- **Core message**: if / elif 必须位于循环体内，才能每次输入后反馈。
- **Content**: 逐字呈现 `互动实践：加入大小提示`；`把 if / elif 放进循环体`；`1`；`DO`；`每次输入后给出大小提示`；`2`；`大小判断应该放在 while 的里面还是外面？`；`用偏小、偏大、正确三类输入测试`；`3`；`LessonCraft AI · STEP-04`；`SLIDE-10`。

#### Slide 11 - 调试挑战：为什么它停不下来？

- **Audience move**: 从写代码 → 建立按条件、缩进、变量更新排查循环问题的意识。
- **Layout**: 大问题居中，三条错误现象作为诊断清单；使用 bug 状态标识但不添加新说明。
- **Title**: 调试挑战：为什么它停不下来？
- **Core message**: 循环不停止时，先检查条件、缩进和变量更新。
- **Content**: 逐字呈现 `调试挑战：为什么它停不下来？`；`?`；`先检查哪一项：条件、缩进，还是变量更新？`；`●  把 while 写成 if，导致代码只判断一次`；`●  忘记给循环体缩进`；`●  条件永远为 True，形成无限循环`；`LessonCraft AI · STEP-04`；`SLIDE-11`。

### Part 5: 完整项目与学生任务

#### Slide 12 - 完整版本：加入大小提示

- **Audience move**: 从局部任务 → 能阅读完整项目并对应三个完成标准。
- **Layout**: 最大化代码控制台，右侧窄列呈现三条验收提示；代码使用 22px 等宽字体且禁止自动换行。
- **Title**: 完整版本：加入大小提示
- **Core message**: 输入和大小判断都在循环体内，猜中后离开循环。
- **Content**: 逐字呈现标题；以下代码块逐字符保持不变：

```text
 1  answer = 7
 2  guess = 0
 3  
 4  while guess != answer:
 5      guess = int(input("请输入 1～10 的数字："))
 6      if guess < answer:
 7          print("太小了")
 8      elif guess > answer:
 9          print("太大了")
10  
11  print("猜对了！")
```

  逐字呈现 `代码来源` 与 `CODE-02`；`●  循环读取输入`；`●  if / elif 给出反馈`；`●  猜中后退出并祝贺`；`LessonCraft AI · STEP-05`；`SLIDE-12`。

#### Slide 13 - 学生动手：完成并测试游戏

- **Audience move**: 从阅读完整代码 → 独立完成作品并用三类输入进行同伴测试。
- **Layout**: 左侧深色任务主卡，右侧浅色完成检查卡，底部黄色动手行动条。
- **Title**: 学生动手：完成并测试游戏
- **Core message**: 完成作品后用偏小、偏大、正确三类输入验证。
- **Content**: 逐字呈现 `学生动手：完成并测试游戏`；`YOUR MISSION`；`完成检查`；`交换游戏，用偏小、偏大、正确三类输入测试，并记录一次发现。`；`●  测试偏小输入`；`●  测试偏大输入`；`●  测试正确输入`；`完成后与同伴交换测试，并记录一个发现。`；`动手做`；`LessonCraft AI · STEP-05`；`SLIDE-13`。

### Part 6: 总结与课后挑战

#### Slide 14 - 记住这三件事

- **Audience move**: 从项目完成 → 用三条标准术语复述 while 的继续、判断与变量更新。
- **Layout**: 深海蓝总结页，三个黄色编号节点形成纵向知识链，底部蓝色复述提示条。
- **Title**: 记住这三件事
- **Core message**: while 的条件、重新判断和变量更新共同决定循环何时停止。
- **Content**: 逐字呈现 `记住这三件事`；`while 循环会在条件为 True 时重复执行一组代码。`；`1`；`循环条件决定循环是否继续执行，每次循环前都会重新判断。`；`2`；`循环变量是在循环过程中被更新、并帮助循环最终停止的变量。`；`3`；`用一句话说明 while 循环何时继续、何时停止。`；`SLIDE-14`。

#### Slide 15 - 课后挑战：让游戏更完整

- **Audience move**: 从课堂作品 → 明确课后升级任务和两项完成检查。
- **Layout**: 任务关卡收尾页；左侧主任务卡、右侧完成检查卡，使用挑战等级与进度装饰但不添加文字。
- **Title**: 课后挑战：让游戏更完整
- **Core message**: 在保留原有功能的前提下增加猜测次数统计。
- **Content**: 逐字呈现 `课后挑战：让游戏更完整`；`YOUR MISSION`；`完成检查`；`在完整游戏中增加猜测次数统计，并在猜中后显示次数。`；`●  保留原有功能`；`●  说明你新增了什么`；`LessonCraft AI · STEP-06`；`SLIDE-15`。

## X. Speaker Notes Requirements

- **Filename**: match each SVG filename under `notes/`
- **Content**: 从源 PPTX 的 15 页 Speaker Notes 逐页、逐项复制；保留“讲解重点、课堂提问、演示动作、常见错误、时间建议、下一页过渡、来源”全部文字，不重新生成或改写。
- **Total duration**: 90 分钟课程；逐页备注中的时间建议合计 55 分钟，仅表示实际投屏讲解建议时间，其余时间用于学生操作、巡视与课堂转换。
- **Notes style**: interactive；简短、可操作、非逐字稿。
- **Presentation purpose**: instruct；现场讲解、预测、演示、动手实践和复盘。
