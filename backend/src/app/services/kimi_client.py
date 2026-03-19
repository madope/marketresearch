from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
import time

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_app_logger

T = TypeVar("T")


@dataclass
class LLMResult(Generic[T]):
    value: T
    status: str
    message: str | None = None
    provider: str | None = None
    model: str | None = None
    method: str | None = None
    prompt: str | None = None


class KimiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.kimi_model
        self._logger = get_app_logger("llm")
        self._enabled = bool(settings.kimi_api_key)
        self._client = None
        if self._enabled:
            self._client = OpenAI(api_key=settings.kimi_api_key, base_url=settings.kimi_base_url)

    def generate_structured_text(self, prompt: str, fallback: str) -> LLMResult[str]:
        start = time.perf_counter()
        if not self._enabled or self._client is None:
            result = LLMResult(
                value=fallback,
                status="fallback",
                message="模型未启用，已降级到 fallback 文本",
                provider="kimi",
                model=self.model,
                method="text",
                prompt=prompt,
            )
            self._log_call("text", result.status, time.perf_counter() - start, result.message, prompt)
            return result

        try:
            response = self._client.responses.create(
                model=self.model,
                input=prompt,
            )
        except Exception as exc:
            result = LLMResult(
                value=fallback,
                status="error",
                message=f"模型请求失败：{exc}",
                provider="kimi",
                model=self.model,
                method="text",
                prompt=prompt,
            )
            self._log_call("text", result.status, time.perf_counter() - start, result.message, prompt)
            return result
        result = LLMResult(
            value=response.output_text or fallback,
            status="success",
            provider="kimi",
            model=self.model,
            method="text",
            prompt=prompt,
        )
        self._log_call("text", result.status, time.perf_counter() - start, None, prompt, result.value)
        return result

    def generate_json(self, prompt: str, fallback: dict[str, Any]) -> LLMResult[dict[str, Any]]:
        start = time.perf_counter()
        if not self._enabled or self._client is None:
            result = LLMResult(
                value=fallback,
                status="fallback",
                message="模型未启用，已降级到 fallback 数据",
                provider="kimi",
                model=self.model,
                method="json",
                prompt=prompt,
            )
            self._log_call("json", result.status, time.perf_counter() - start, result.message, prompt)
            return result

        try:
            response = self._client.responses.create(
                model=self.model,
                input=f"{prompt}\n\n请只返回合法 JSON，不要输出 Markdown 代码块。",
            )
        except Exception as exc:
            result = LLMResult(
                value=fallback,
                status="error",
                message=f"模型请求失败：{exc}",
                provider="kimi",
                model=self.model,
                method="json",
                prompt=prompt,
            )
            self._log_call("json", result.status, time.perf_counter() - start, result.message, prompt)
            return result
        text = response.output_text or ""
        try:
            result = LLMResult(
                value=json.loads(text),
                status="success",
                provider="kimi",
                model=self.model,
                method="json",
                prompt=prompt,
            )
            self._log_call("json", result.status, time.perf_counter() - start, None, prompt, result.value)
            return result
        except json.JSONDecodeError:
            result = LLMResult(
                value=fallback,
                status="fallback",
                message="模型返回格式异常，已降级到 fallback 数据",
                provider="kimi",
                model=self.model,
                method="json",
                prompt=prompt,
            )
            self._log_call("json", result.status, time.perf_counter() - start, result.message, prompt)
            return result

    def search_web(self, prompt: str, fallback: dict[str, Any]) -> LLMResult[dict[str, Any]]:
        start = time.perf_counter()
        result = LLMResult(
            value=fallback,
            status="fallback",
            message="Kimi provider 当前未启用原生 web search，本轮平台搜索结果已按空结果处理",
            provider="kimi",
            model=self.model,
            method="web_search",
            prompt=prompt,
        )
        self._log_call("web_search", result.status, time.perf_counter() - start, result.message, prompt)
        return result

    def _log_call(
        self,
        method: str,
        status: str,
        elapsed_seconds: float,
        message: str | None,
        prompt: str,
        output: Any | None = None,
    ) -> None:
        prompt_preview = prompt.strip().replace("\n", " ")[:1000]
        output_preview = str(output)[:1000] if output is not None else None
        self._logger.info(
            "llm_call provider=kimi model=%s method=%s status=%s elapsed_ms=%s prompt_preview=%r output_preview=%r message=%r",
            self.model,
            method,
            status,
            int(elapsed_seconds * 1000),
            prompt_preview,
            output_preview,
            message,
        )
