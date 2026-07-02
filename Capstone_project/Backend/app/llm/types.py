"""Shared LLM request, response, and provider error types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol

ProviderName = Literal["anthropic", "groq", "openai"]
LLMComplexity = Literal["simple", "standard", "complex", "critical"]
PROVIDER_NAMES: tuple[ProviderName, ...] = ("anthropic", "groq", "openai")


class LLMFailureKind(str, Enum):
    MISSING_API_KEY = "missing_api_key"
    RATE_LIMIT = "rate_limit"
    TOKEN_LIMIT = "token_limit"
    CONTEXT_LENGTH = "context_length"
    TIMEOUT = "timeout"
    QUOTA = "quota"
    PROVIDER_ERROR = "provider_error"
    NETWORK = "network"
    UNKNOWN = "unknown"


FALLBACK_FAILURE_KINDS = {
    LLMFailureKind.RATE_LIMIT,
    LLMFailureKind.TOKEN_LIMIT,
    LLMFailureKind.CONTEXT_LENGTH,
    LLMFailureKind.TIMEOUT,
    LLMFailureKind.QUOTA,
}


@dataclass(slots=True)
class LLMRequest:
    prompt: str
    request_type: str = "general"
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    preferred_model: str | None = None
    complexity: LLMComplexity = "standard"
    cacheable: bool = False
    user_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderResponse:
    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    actual_cost_usd: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponse:
    content: str
    provider: ProviderName
    model: str
    request_type: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    actual_cost_usd: float | None
    latency_ms: float
    fallback_used: bool
    fallback_provider: ProviderName | None = None
    cache_hit: bool = False
    model_tier: str = "standard"
    routing_reason: str = ""
    quality_guardrail: str = ""


class LLMProviderError(Exception):
    """Provider failure with normalized kind for fallback and user messaging."""

    def __init__(
        self,
        message: str,
        *,
        provider: ProviderName,
        kind: LLMFailureKind = LLMFailureKind.UNKNOWN,
        retryable: bool = False,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.kind = kind
        self.retryable = retryable
        self.status_code = status_code


class LLMProviderClient(Protocol):
    name: ProviderName

    def complete(
        self,
        request: LLMRequest,
        *,
        model: str,
        api_key: str,
        timeout_seconds: float,
    ) -> ProviderResponse:
        """Run one synchronous provider completion call."""
