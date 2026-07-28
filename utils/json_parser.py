"""Resilient parsing for JSON returned by language models."""

from __future__ import annotations

import json
import re
from typing import Any


class JSONParseError(ValueError):
    """Raised when a model response cannot be converted to JSON."""


def parse_json_response(text: str) -> dict[str, Any]:
    """Parse plain JSON, tolerating code fences and surrounding prose."""

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    attempts = [cleaned]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        attempts.append(cleaned[start : end + 1])
    for candidate in attempts:
        try:
            parsed = json.loads(candidate)
            if not isinstance(parsed, dict):
                raise JSONParseError("模型必须返回 JSON 对象")
            return parsed
        except json.JSONDecodeError:
            continue
    raise JSONParseError("无法解析模型返回的 JSON；已尝试移除代码围栏和前后说明")
