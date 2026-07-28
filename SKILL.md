---
name: lessoncraft-ai
description: Generate a consistent, age-appropriate children's programming teaching package from a single Course Blueprint. Use when a teacher needs a lesson plan, student-facing slide deck, per-slide teaching prompts, code examples, exercises, consistency checks, or revisions for a Scratch, Python, or C++ class.
---

# LessonCraft AI

Generate every deliverable from one validated `CourseBlueprint`.

## Workflow

1. Collect language, topic, age, prior knowledge, duration, core goal, teaching style, slide limit, and optional requirements.
2. Validate the input before generation.
3. Create the Course Blueprint first. Treat it as the only source of truth.
4. Derive the lesson plan and slide deck only from the Blueprint.
5. Reuse terminology, sequence, source IDs, and exact code examples.
6. Run deterministic consistency checks before export.
7. For revisions, update the Blueprint first, record `affected_ids`, regenerate derived content, and rerun checks.
8. Export editable PPTX, DOCX, JSON, and source code.

## Non-negotiable rules

- Do not introduce objectives or knowledge points outside the Blueprint.
- Do not rewrite code examples inside lesson plans or slides; reference `code_example_id`.
- Preserve `step_id`, `objective_ids`, and `knowledge_ids` on derived content.
- Keep lesson-flow order and total time aligned with the requested duration.
- Ensure each objective maps to a lesson step, a slide, and an activity or exercise.
- Use Demo Mode when API credentials are absent.

## Run

Install `requirements.txt`, copy `.env.example` to `.env`, then run:

```bash
streamlit run app.py
```

Use the repository README for product setup, API configuration, and tests.
