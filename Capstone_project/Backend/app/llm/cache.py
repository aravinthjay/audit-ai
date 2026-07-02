"""Tiny in-process LLM response cache for explicitly safe repeat calls."""

from __future__ import annotations

import time
from dataclasses import replace
from hashlib import sha256

from app.llm.types import LLMResponse, ProviderName


class LLMResponseCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, LLMResponse]] = {}

    def key(self, provider: ProviderName, model: str, prompt: str, system_prompt: str | None) -> str:
        digest = sha256()
        digest.update(provider.encode("utf-8"))
        digest.update(model.encode("utf-8"))
        digest.update((system_prompt or "").encode("utf-8"))
        digest.update(prompt.encode("utf-8"))
        return digest.hexdigest()

    def get(self, key: str, ttl_seconds: int) -> LLMResponse | None:
        item = self._items.get(key)
        if not item:
            return None
        created_at, response = item
        if time.time() - created_at > ttl_seconds:
            self._items.pop(key, None)
            return None
        return replace(response, cache_hit=True, latency_ms=0.0)

    def set(self, key: str, response: LLMResponse) -> None:
        self._items[key] = (time.time(), response)

    def clear(self) -> None:
        self._items.clear()


response_cache = LLMResponseCache()
