from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_app_logger
from app.services.kimi_client import LLMResult
import time


class VolcengineArkClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.ark_model
        self.timeout = settings.request_timeout_seconds
        self._logger = get_app_logger("llm")
        self._enabled = bool(settings.ark_api_key)
        self._client = None
        if self._enabled:
            self._client = OpenAI(
                api_key=settings.ark_api_key,
                base_url=settings.ark_base_url,
                timeout=self.timeout,
            )

    def generate_structured_text(self, prompt: str, fallback: str) -> LLMResult[str]:
        start = time.perf_counter()
        if not self._enabled or self._client is None:
            result = LLMResult(
                value=fallback,
                status="fallback",
                message="火山方舟模型未启用，已降级到 fallback 文本",
                provider="volcengine",
                model=self.model,
                method="text",
                prompt=prompt,
            )
            self._log_call("text", result.status, time.perf_counter() - start, result.message, prompt)
            return result

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            result = LLMResult(
                value=fallback,
                status="error",
                message=f"火山方舟模型请求失败：{exc}",
                provider="volcengine",
                model=self.model,
                method="text",
                prompt=prompt,
            )
            self._log_call("text", result.status, time.perf_counter() - start, result.message, prompt)
            return result
        content = response.choices[0].message.content if response.choices else ""
        result = LLMResult(
            value=content or fallback,
            status="success",
            provider="volcengine",
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
                message="火山方舟模型未启用，已降级到 fallback 数据",
                provider="volcengine",
                model=self.model,
                method="json",
                prompt=prompt,
            )
            self._log_call("json", result.status, time.perf_counter() - start, result.message, prompt)
            return result

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n请只返回合法 JSON，不要输出 Markdown 代码块。",
                    }
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            result = LLMResult(
                value=fallback,
                status="error",
                message=f"火山方舟模型请求失败：{exc}",
                provider="volcengine",
                model=self.model,
                method="json",
                prompt=prompt,
            )
            self._log_call("json", result.status, time.perf_counter() - start, result.message, prompt)
            return result
        text = response.choices[0].message.content if response.choices else ""
        try:
            result = LLMResult(
                value=json.loads(text),
                status="success",
                provider="volcengine",
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
                message="火山方舟模型返回格式异常，已降级到 fallback 数据",
                provider="volcengine",
                model=self.model,
                method="json",
                prompt=prompt,
            )
            self._log_call("json", result.status, time.perf_counter() - start, result.message, prompt)
            return result

    def search_web(self, prompt: str, fallback: dict[str, Any]) -> LLMResult[dict[str, Any]]:
        start = time.perf_counter()
        if not self._enabled or self._client is None:
            result = LLMResult(
                value=fallback,
                status="fallback",
                message="火山方舟模型未启用原生 web search，已降级到 fallback 平台发现",
                provider="volcengine",
                model=self.model,
                method="web_search",
                prompt=prompt,
            )
            self._log_call("web_search", result.status, time.perf_counter() - start, result.message, prompt)
            return result

        try:
            response = self._client.responses.create(
                model=self.model,
                input=(
                    f"{prompt}\n\n"
                    "请使用 web search 实时搜索与该调研主题相关的平台，"
                    "只返回合法 JSON，不要输出 Markdown 代码块。"
                ),
                tools=[{"type": "web_search"}],
            )
        except Exception as exc:
            result = LLMResult(
                value=fallback,
                status="error",
                message=f"火山方舟 web search 请求失败：{exc}",
                provider="volcengine",
                model=self.model,
                method="web_search",
                prompt=prompt,
            )
            self._log_call("web_search", result.status, time.perf_counter() - start, result.message, prompt)
            return result

        text = response.output_text or ""
        try:
            result = LLMResult(
                value=json.loads(text),
                status="success",
                provider="volcengine",
                model=self.model,
                method="web_search",
                prompt=prompt,
            )
            self._log_call("web_search", result.status, time.perf_counter() - start, None, prompt, result.value)
            return result
        except json.JSONDecodeError:
            result = LLMResult(
                value=fallback,
                status="fallback",
                message="火山方舟 web search 返回格式异常，已降级到 fallback 平台发现",
                provider="volcengine",
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
            "llm_call provider=volcengine model=%s method=%s status=%s elapsed_ms=%s prompt_preview=%r output_preview=%r message=%r",
            self.model,
            method,
            status,
            int(elapsed_seconds * 1000),
            prompt_preview,
            output_preview,
            message,
        )
