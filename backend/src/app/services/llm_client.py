from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.services.ark_client import VolcengineArkClient
from app.services.kimi_client import KimiClient, LLMResult


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.provider_name = settings.llm_provider
        if self.provider_name == "volcengine":
            self._provider = VolcengineArkClient()
        else:
            self.provider_name = "kimi"
            self._provider = KimiClient()

    def generate_structured_text(self, prompt: str, fallback: str) -> LLMResult[str]:
        return self._provider.generate_structured_text(prompt, fallback)

    def generate_json(self, prompt: str, fallback: dict[str, Any]) -> LLMResult[dict[str, Any]]:
        return self._provider.generate_json(prompt, fallback)

    def search_web(self, prompt: str, fallback: dict[str, Any]) -> LLMResult[dict[str, Any]]:
        return self._provider.search_web(prompt, fallback)
