"""Provider HTTP helpers and error normalization."""

from __future__ import annotations

from typing import Any

import requests

from app.llm.types import LLMFailureKind, LLMProviderError, ProviderName


def classify_provider_error(status_code: int | None, message: str) -> LLMFailureKind:
    lowered = message.lower()
    if status_code == 429 or "rate limit" in lowered or "rate_limit" in lowered or "too many requests" in lowered:
        if "quota" in lowered or "billing" in lowered or "insufficient" in lowered:
            return LLMFailureKind.QUOTA
        return LLMFailureKind.RATE_LIMIT
    if status_code in (408, 504) or "timeout" in lowered or "timed out" in lowered:
        return LLMFailureKind.TIMEOUT
    if status_code == 413 or "context length" in lowered or "context_length" in lowered or "maximum context" in lowered:
        return LLMFailureKind.CONTEXT_LENGTH
    if "token limit" in lowered or "token_limit" in lowered or "max tokens" in lowered or "too many tokens" in lowered:
        return LLMFailureKind.TOKEN_LIMIT
    if "quota" in lowered or "billing quota" in lowered or "insufficient quota" in lowered:
        return LLMFailureKind.QUOTA
    if status_code in (401, 403) or "invalid_api_key" in lowered or "incorrect api key" in lowered or "invalid x-api-key" in lowered or "authentication" in lowered or "unauthorized" in lowered:
        return LLMFailureKind.AUTH
    if status_code == 404 or "not_found" in lowered or "not found" in lowered or "does not exist" in lowered:
        return LLMFailureKind.MODEL_NOT_FOUND
    if status_code and status_code >= 500:
        return LLMFailureKind.PROVIDER_ERROR
    return LLMFailureKind.UNKNOWN


def response_error(provider: ProviderName, response: requests.Response) -> LLMProviderError:
    try:
        payload: Any = response.json()
    except ValueError:
        payload = response.text
    message = str(payload)
    kind = classify_provider_error(response.status_code, message)
    return LLMProviderError(
        f"{provider} request failed: {message[:500]}",
        provider=provider,
        kind=kind,
        retryable=kind
        in {
            LLMFailureKind.RATE_LIMIT,
            LLMFailureKind.TOKEN_LIMIT,
            LLMFailureKind.CONTEXT_LENGTH,
            LLMFailureKind.TIMEOUT,
            LLMFailureKind.QUOTA,
            LLMFailureKind.PROVIDER_ERROR,
        },
        status_code=response.status_code,
    )


def request_exception(provider: ProviderName, exc: requests.RequestException) -> LLMProviderError:
    if isinstance(exc, requests.Timeout):
        kind = LLMFailureKind.TIMEOUT
    else:
        kind = classify_provider_error(None, str(exc)) or LLMFailureKind.NETWORK
        if kind == LLMFailureKind.UNKNOWN:
            kind = LLMFailureKind.NETWORK
    return LLMProviderError(
        f"{provider} request failed: {exc}",
        provider=provider,
        kind=kind,
        retryable=True,
    )
