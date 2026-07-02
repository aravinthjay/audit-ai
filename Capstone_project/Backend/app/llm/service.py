"""LLM orchestration service: routing, fallback, cache, and telemetry."""

from __future__ import annotations

import logging
import time
from dataclasses import replace

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import LLMCallLog
from app.db.session import SessionLocal
from app.llm.cache import response_cache
from app.llm.pricing import estimate_cost_usd
from app.llm.providers import AnthropicProvider, GroqProvider, OpenAIProvider
from app.llm.routing import prepare_request_for_model, quality_guardrail, route_model
from app.llm.settings_store import api_key_for, get_llm_settings, provider_statuses
from app.llm.tokenization import estimate_tokens
from app.llm.types import (
    FALLBACK_FAILURE_KINDS,
    LLMFailureKind,
    LLMProviderClient,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    ProviderName,
)

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(
        self,
        providers: dict[ProviderName, LLMProviderClient] | None = None,
        session_factory: sessionmaker | None = SessionLocal,
    ) -> None:
        self.providers = providers or {
            "anthropic": AnthropicProvider(),
            "groq": GroqProvider(),
            "openai": OpenAIProvider(),
        }
        self.session_factory = session_factory

    def provider_statuses(self) -> list[dict]:
        return provider_statuses()

    def complete(self, request: LLMRequest) -> LLMResponse:
        prepared = prepare_request_for_model(request)
        runtime = self._runtime_settings()
        default_provider: ProviderName = runtime["default_provider"]
        fallback_enabled = bool(runtime["fallback_enabled"])
        ordered_providers: list[ProviderName] = [default_provider]
        if fallback_enabled:
            ordered_providers.extend(runtime["fallback_order"])

        last_error: LLMProviderError | None = None
        seen: set[ProviderName] = set()
        for provider in ordered_providers:
            if provider in seen:
                continue
            seen.add(provider)
            model, model_tier, routing_reason = route_model(provider, prepared)
            fallback_used = provider != default_provider
            key = api_key_for(provider).strip()
            if not key:
                error = LLMProviderError(
                    f"{provider} API key is not configured.",
                    provider=provider,
                    kind=LLMFailureKind.MISSING_API_KEY,
                    retryable=False,
                )
                self._record_call(
                    prepared,
                    provider=provider,
                    model=model,
                    model_tier=model_tier,
                    routing_reason=routing_reason,
                    success=False,
                    latency_ms=0.0,
                    fallback_used=fallback_used,
                    fallback_provider=provider if fallback_used else None,
                    error_message=str(error),
                    quality_guardrail_text=quality_guardrail(prepared),
                )
                raise error

            cache_key = response_cache.key(provider, model, prepared.prompt, prepared.system_prompt)
            if prepared.cacheable and settings.LLM_CACHE_ENABLED:
                cached = response_cache.get(cache_key, settings.LLM_CACHE_TTL_SECONDS)
                if cached:
                    cached = replace(
                        cached,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        estimated_cost_usd=0.0,
                        actual_cost_usd=None,
                        cache_hit=True,
                        latency_ms=0.0,
                    )
                    self._record_call(
                        prepared,
                        provider=provider,
                        model=model,
                        model_tier=model_tier,
                        routing_reason=routing_reason,
                        success=True,
                        latency_ms=0.0,
                        prompt_tokens=0,
                        completion_tokens=0,
                        estimated_cost_usd=0.0,
                        actual_cost_usd=None,
                        fallback_used=fallback_used,
                        fallback_provider=provider if fallback_used else None,
                        cache_hit=True,
                        quality_guardrail_text=cached.quality_guardrail,
                    )
                    logger.info("LLM cache hit provider=%s model=%s request_type=%s", provider, model, request.request_type)
                    return cached

            started = time.perf_counter()
            try:
                provider_response = self.providers[provider].complete(
                    prepared,
                    model=model,
                    api_key=key,
                    timeout_seconds=settings.LLM_REQUEST_TIMEOUT_SECONDS,
                )
            except LLMProviderError as exc:
                last_error = exc
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                self._record_call(
                    prepared,
                    provider=provider,
                    model=model,
                    model_tier=model_tier,
                    routing_reason=routing_reason,
                    success=False,
                    latency_ms=latency_ms,
                    fallback_used=fallback_used,
                    fallback_provider=provider if fallback_used else None,
                    error_message=str(exc),
                    quality_guardrail_text=quality_guardrail(prepared),
                )
                can_fallback = fallback_enabled and exc.kind in FALLBACK_FAILURE_KINDS
                if can_fallback:
                    logger.warning(
                        "LLM provider %s failed with %s; trying fallback provider",
                        provider,
                        exc.kind.value,
                    )
                    continue
                raise

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            prompt_tokens = provider_response.prompt_tokens
            if prompt_tokens is None:
                prompt_tokens = estimate_tokens(
                    f"{prepared.system_prompt or ''}\n\n{prepared.prompt}".strip()
                )
            completion_tokens = provider_response.completion_tokens
            if completion_tokens is None:
                completion_tokens = estimate_tokens(provider_response.content)
            total_tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)
            estimated_cost = estimate_cost_usd(
                provider_response.model,
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
            )
            response = LLMResponse(
                content=provider_response.content,
                provider=provider,
                model=provider_response.model,
                request_type=prepared.request_type,
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
                actual_cost_usd=provider_response.actual_cost_usd,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                fallback_provider=provider if fallback_used else None,
                cache_hit=False,
                model_tier=model_tier,
                routing_reason=routing_reason,
                quality_guardrail=quality_guardrail(prepared),
            )
            self._record_call(
                prepared,
                provider=provider,
                model=response.model,
                model_tier=model_tier,
                routing_reason=routing_reason,
                success=True,
                latency_ms=latency_ms,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                estimated_cost_usd=estimated_cost,
                actual_cost_usd=response.actual_cost_usd,
                fallback_used=fallback_used,
                fallback_provider=provider if fallback_used else None,
                cache_hit=False,
                quality_guardrail_text=response.quality_guardrail,
            )
            if prepared.cacheable and settings.LLM_CACHE_ENABLED:
                response_cache.set(cache_key, response)
            logger.info(
                "LLM provider used provider=%s model=%s request_type=%s fallback=%s tokens=%s",
                provider,
                response.model,
                response.request_type,
                fallback_used,
                total_tokens,
            )
            return response

        if last_error:
            raise last_error
        raise LLMProviderError(
            "No LLM provider could complete the request.",
            provider=default_provider,
            kind=LLMFailureKind.UNKNOWN,
        )

    def _runtime_settings(self) -> dict:
        if not self.session_factory:
            return {
                "default_provider": settings.DEFAULT_LLM_PROVIDER,
                "fallback_enabled": settings.ENABLE_LLM_FALLBACK,
                "fallback_order": settings.LLM_FALLBACK_ORDER,
            }
        db = self.session_factory()
        try:
            return get_llm_settings(db)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM runtime settings unavailable; using environment defaults: %s", exc)
            return {
                "default_provider": settings.DEFAULT_LLM_PROVIDER,
                "fallback_enabled": settings.ENABLE_LLM_FALLBACK,
                "fallback_order": settings.LLM_FALLBACK_ORDER,
            }
        finally:
            db.close()

    def _record_call(
        self,
        request: LLMRequest,
        *,
        provider: ProviderName,
        model: str,
        model_tier: str,
        routing_reason: str,
        success: bool,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        actual_cost_usd: float | None = None,
        fallback_used: bool = False,
        fallback_provider: ProviderName | None = None,
        cache_hit: bool = False,
        error_message: str | None = None,
        quality_guardrail_text: str = "",
    ) -> None:
        if not self.session_factory:
            return
        db = self.session_factory()
        try:
            db.add(
                LLMCallLog(
                    provider_name=provider,
                    model_name=model,
                    request_type=request.request_type,
                    prompt_tokens=int(prompt_tokens or 0),
                    completion_tokens=int(completion_tokens or 0),
                    total_tokens=int(prompt_tokens or 0) + int(completion_tokens or 0),
                    estimated_cost_usd=float(estimated_cost_usd or 0.0),
                    actual_cost_usd=actual_cost_usd,
                    latency_ms=float(latency_ms or 0.0),
                    success=success,
                    error_message=(error_message or "")[:2000] or None,
                    fallback_used=fallback_used,
                    fallback_provider=fallback_provider,
                    cache_hit=cache_hit,
                    model_tier=model_tier,
                    routing_reason=routing_reason,
                    quality_guardrail=quality_guardrail_text,
                    user_id=request.user_id or request.metadata.get("user_id"),
                    session_id=request.session_id or request.metadata.get("session_id"),
                    request_id=request.request_id or request.metadata.get("request_id"),
                )
            )
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.warning("Failed to record LLM telemetry: %s", exc)
        finally:
            db.close()


_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _service
    if _service is None:
        _service = LLMService()
    return _service
