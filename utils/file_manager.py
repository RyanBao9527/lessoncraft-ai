"""File loading, safe naming, and in-memory serialization helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def safe_filename(value: str, fallback: str = "lessoncraft") -> str:
    """Create a portable filename without trusting user-supplied paths."""

    name = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", value.strip(), flags=re.UNICODE)
    name = name.strip(".-_")[:80]
    return name or fallback


def load_json(path: Path) -> dict[str, Any]:
    """Load UTF-8 JSON and preserve useful error context."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取示例数据 {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"示例数据必须是 JSON 对象: {path}")
    return data


def load_demo_package() -> dict[str, Any]:
    """Load the fixed package used by no-key Demo Mode."""

    from models.blueprint import CourseBlueprint
    from services.consistency_checker import ConsistencyChecker
    from services.course_generator import derive_lesson_plan, derive_slide_deck

    course_input = load_json(PROJECT_ROOT / "examples" / "sample_input.json")
    blueprint = CourseBlueprint.model_validate(
        load_json(PROJECT_ROOT / "examples" / "sample_output" / "blueprint.json")
    )
    slide_deck = derive_slide_deck(blueprint)
    lesson_plan = derive_lesson_plan(blueprint, slide_deck)
    report = ConsistencyChecker().check(blueprint, lesson_plan, slide_deck)
    return {
        "course_input": course_input,
        "blueprint": blueprint.model_dump(mode="json"),
        "lesson_plan": lesson_plan.model_dump(mode="json"),
        "slide_deck": slide_deck.model_dump(mode="json"),
        "consistency_report": report.model_dump(mode="json"),
    }
