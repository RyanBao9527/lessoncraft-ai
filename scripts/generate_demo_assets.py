"""Regenerate fixed offline demo outputs from the sample Blueprint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exporters.docx_exporter import export_lesson_plan_docx
from exporters.pptx_exporter import export_slide_deck_pptx
from models.blueprint import CourseBlueprint
from models.lesson_plan import LessonPlan
from models.slide_deck import SlideDeck
from utils.file_manager import load_demo_package


def main() -> None:
    """Write reproducible sample JSON, PPTX, DOCX, and Python code."""

    package = load_demo_package()
    blueprint = CourseBlueprint.model_validate(package["blueprint"])
    lesson_plan = LessonPlan.model_validate(package["lesson_plan"])
    slide_deck = SlideDeck.model_validate(package["slide_deck"])
    destination = PROJECT_ROOT / "examples" / "sample_output"
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("blueprint.json", package["blueprint"]),
        ("lesson_plan.json", package["lesson_plan"]),
        ("slide_deck.json", package["slide_deck"]),
        ("consistency_report.json", package["consistency_report"]),
    ):
        (destination / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (destination / "teaching_package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (destination / "guess-number-lesson-plan.docx").write_bytes(
        export_lesson_plan_docx(blueprint, lesson_plan, slide_deck)
    )
    (destination / "guess-number-slides.pptx").write_bytes(
        export_slide_deck_pptx(blueprint, slide_deck)
    )
    code = "\n\n".join(
        f"# {item.id} · {item.title}\n{item.code}" for item in blueprint.code_examples
    )
    (destination / "guess_number_examples.py").write_text(code + "\n", encoding="utf-8")
    print(f"Generated demo assets in {destination}")


if __name__ == "__main__":
    main()
