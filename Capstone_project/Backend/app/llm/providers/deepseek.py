"""DeepSeek OpenAI-compatible chat completions client."""

from __future__ import annotations

from typing import Any

import requests

from app.core.config import settings
from app.llm.providers.base import request_exception, response_error
from app.llm.types import LLMRequest, ProviderResponse

# Verdict agents must return strict JSON; enable provider JSON mode for them so
# weaker models don't wrap the object in prose or markdown fences.
JSON_REQUEST_TYPES = {"adjudication", "verification"}


class DeepSeekProvider:
    name = "deepseek"
    endpoint = "https://api.deepseek.com/v1/chat/completions"

    def complete(
        self,
        request: LLMRequest,
        *,
        model: str,
        api_key: str,
        timeout_seconds: float,
    ) -> ProviderResponse:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": settings.DEEPSEEK_TEMPERATURE if request.temperature is None else request.temperature,
            "max_tokens": request.max_tokens or 4000,
        }
        if request.request_type.lower() in JSON_REQUEST_TYPES:
            body["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(
                self.endpoint,
                headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json=body,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise request_exception(self.name, exc) from exc

        if not response.ok:
            raise response_error(self.name, response)

        payload = response.json()
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = payload.get("usage") or {}
        return ProviderResponse(
            content=str(message.get("content") or ""),
            model=str(payload.get("model") or model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw=payload,
        )
