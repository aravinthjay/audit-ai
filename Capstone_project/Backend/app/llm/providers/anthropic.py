"""Anthropic Messages API client."""

from __future__ import annotations

from typing import Any

import requests

from app.llm.providers.base import request_exception, response_error
from app.llm.types import LLMRequest, ProviderResponse


class AnthropicProvider:
    name = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"

    def complete(
        self,
        request: LLMRequest,
        *,
        model: str,
        api_key: str,
        timeout_seconds: float,
    ) -> ProviderResponse:
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens or 4000,
            "temperature": 0.7 if request.temperature is None else request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system_prompt:
            body["system"] = request.system_prompt

        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise request_exception(self.name, exc) from exc

        if not response.ok:
            raise response_error(self.name, response)

        payload = response.json()
        content = "".join(
            item.get("text", "")
            for item in payload.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text"
        )
        usage = payload.get("usage") or {}
        return ProviderResponse(
            content=content,
            model=str(payload.get("model") or model),
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            raw=payload,
        )
