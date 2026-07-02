"""Model routing and quality-preserving prompt guardrails."""

from __future__ import annotations

from app.core.config import settings
from app.llm.tokenization import compact_prompt, estimate_tokens
from app.llm.types import LLMRequest, ProviderName

CRITICAL_REQUEST_TYPES = {
    "adjudication",
    "verification",
    "final_report",
    "compliance",
    "audit_verdict",
}
SIMPLE_REQUEST_TYPES = {
    "classification",
    "summarization",
    "settings_preview",
    "health_check",
}


def provider_model(provider: ProviderName, *, lightweight: bool) -> str:
    if provider == "anthropic":
        return settings.CLAUDE_MODEL_LIGHTWEIGHT if lightweight else settings.CLAUDE_MODEL_REASONING
    if provider == "groq":
        return settings.GROQ_MODEL_LIGHTWEIGHT if lightweight else settings.GROQ_MODEL_REASONING
    if provider == "gemini":
        return settings.GEMINI_MODEL_LIGHTWEIGHT if lightweight else settings.GEMINI_MODEL_REASONING
    if provider == "deepseek":
        return settings.DEEPSEEK_MODEL_LIGHTWEIGHT if lightweight else settings.DEEPSEEK_MODEL_REASONING
    return settings.OPENAI_MODEL_LIGHTWEIGHT if lightweight else settings.OPENAI_MODEL_REASONING


def route_model(provider: ProviderName, request: LLMRequest) -> tuple[str, str, str]:
    """Choose a model without silently trading away quality."""
    if request.preferred_model:
        return request.preferred_model, "explicit", "caller supplied an explicit model"

    request_type = request.request_type.lower()
    high_risk = request.complexity in ("complex", "critical") or request_type in CRITICAL_REQUEST_TYPES
    prompt_tokens = estimate_tokens(request.prompt)

    if high_risk:
        return (
            provider_model(provider, lightweight=False),
            "reasoning",
            "complex or audit-critical request uses the stronger reasoning model",
        )

    if request.complexity == "simple" or request_type in SIMPLE_REQUEST_TYPES:
        return (
            provider_model(provider, lightweight=True),
            "lightweight",
            "simple, low-risk request uses the lightweight model",
        )

    if prompt_tokens < 1200:
        return (
            provider_model(provider, lightweight=True),
            "lightweight",
            "short standard request uses the lower-latency model with guardrails",
        )

    return (
        provider_model(provider, lightweight=False),
        "reasoning",
        "larger context uses the stronger reasoning model",
    )


def quality_guardrail(request: LLMRequest) -> str:
    request_type = request.request_type.lower()
    if request.complexity == "critical" or request_type in CRITICAL_REQUEST_TYPES:
        return (
            "Use all material context, preserve citations and evidence IDs, state uncertainty, "
            "and do not clear or escalate a case without explicit support."
        )
    return (
        "Be concise, preserve important evidence and citations, and state when context is insufficient."
    )


def prepare_request_for_model(request: LLMRequest) -> LLMRequest:
    prompt = compact_prompt(request.prompt, settings.LLM_MAX_PROMPT_TOKENS)
    guardrail = quality_guardrail(request)
    system_parts = [guardrail]
    if request.system_prompt:
        system_parts.append(request.system_prompt.strip())

    return LLMRequest(
        prompt=prompt,
        request_type=request.request_type,
        system_prompt="\n\n".join(part for part in system_parts if part),
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        preferred_model=request.preferred_model,
        complexity=request.complexity,
        cacheable=request.cacheable,
        user_id=request.user_id,
        session_id=request.session_id,
        request_id=request.request_id,
        metadata=dict(request.metadata),
    )
