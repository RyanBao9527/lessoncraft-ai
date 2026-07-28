"""Minimal OpenAI-compatible chat client with JSON repair."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI

from utils.json_parser import JSONParseError, parse_json_response


class LLMConfigurationError(RuntimeError):
    """Raised when required environment variables are absent."""


class LLMGenerationError(RuntimeError):
    """Raised when an API call or JSON repair cannot complete."""


class LLMClient:
    """OpenAI-compatible client configured entirely through environment variables."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int = 1,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "") or None
        self.model = model or os.getenv("LLM_MODEL", "")
        self.max_retries = max_retries
        if not self.api_key:
            raise LLMConfigurationError(
                "未配置 LLM_API_KEY。请在 .env 中配置模型，或在页面启用 Demo Mode。"
            )
        if not self.model:
            raise LLMConfigurationError(
                "未配置 LLM_MODEL。请填写兼容服务提供的模型名称。"
            )
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=90.0)

    def _complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            raise LLMGenerationError(f"模型调用失败: {exc}") from exc
        content = response.choices[0].message.content
        if not content:
            raise LLMGenerationError("模型返回了空内容")
        return content

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Request JSON and run one focused repair call if parsing fails."""

        raw = self._complete(system_prompt, user_prompt)
        try:
            return parse_json_response(raw)
        except JSONParseError as first_error:
            last_error: Exception = first_error
            for _ in range(self.max_retries):
                repair_prompt = (
                    "下面内容不是可解析的严格 JSON。请只修复 JSON 语法和结构，"
                    "不得改动事实、ID、顺序或代码。只输出修复后的 JSON：\n\n"
                    f"{raw}"
                )
                repaired = self._complete(
                    "你是 JSON 修复器。只输出一个严格 JSON 对象，不输出 Markdown。", repair_prompt
                )
                try:
                    return parse_json_response(repaired)
                except JSONParseError as exc:
                    last_error = exc
            raise LLMGenerationError(f"模型 JSON 解析和修复均失败: {last_error}") from last_error
