"""Runtime LLM settings persistence and provider status helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RuntimeSetting, User
from app.llm.types import PROVIDER_NAMES, ProviderName

LLM_SETTINGS_KEY = "llm"

PROVIDER_LABELS: dict[ProviderName, str] = {
    "anthropic": "Claude / Anthropic",
    "groq": "Groq",
    "openai": "OpenAI",
}
PROVIDER_KEY_ENV: dict[ProviderName, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def normalize_provider(value: str | None) -> ProviderName:
    lowered = (value or "anthropic").strip().lower()
    if lowered not in PROVIDER_NAMES:
        return "anthropic"
    return lowered  # type: ignore[return-value]


def normalize_fallback_order(default_provider: ProviderName, order: list[str] | tuple[str, ...]) -> list[ProviderName]:
    normalized: list[ProviderName] = []
    for provider in order:
        typed = normalize_provider(provider)
        if typed == default_provider or typed in normalized:
            continue
        normalized.append(typed)
    for provider in PROVIDER_NAMES:
        if provider != default_provider and provider not in normalized:
            normalized.append(provider)
    return normalized


def api_key_for(provider: ProviderName) -> str:
    return str(getattr(settings, PROVIDER_KEY_ENV[provider], "") or "")


def provider_configured(provider: ProviderName) -> bool:
    return bool(api_key_for(provider).strip())


def provider_models(provider: ProviderName) -> tuple[str, str]:
    if provider == "anthropic":
        return settings.CLAUDE_MODEL_REASONING, settings.CLAUDE_MODEL_LIGHTWEIGHT
    if provider == "groq":
        return settings.GROQ_MODEL_REASONING, settings.GROQ_MODEL_LIGHTWEIGHT
    return settings.OPENAI_MODEL_REASONING, settings.OPENAI_MODEL_LIGHTWEIGHT


def provider_statuses() -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for provider in PROVIDER_NAMES:
        reasoning_model, lightweight_model = provider_models(provider)
        configured = provider_configured(provider)
        statuses.append(
            {
                "id": provider,
                "label": PROVIDER_LABELS[provider],
                "configured": configured,
                "reasoning_model": reasoning_model,
                "lightweight_model": lightweight_model,
                "missing_env": None if configured else PROVIDER_KEY_ENV[provider],
            }
        )
    return statuses


def default_llm_settings() -> dict[str, Any]:
    default_provider = normalize_provider(settings.DEFAULT_LLM_PROVIDER)
    return {
        "default_provider": default_provider,
        "fallback_enabled": bool(settings.ENABLE_LLM_FALLBACK),
        "fallback_order": normalize_fallback_order(default_provider, settings.LLM_FALLBACK_ORDER),
    }


def get_llm_settings(db: Session) -> dict[str, Any]:
    row = db.get(RuntimeSetting, LLM_SETTINGS_KEY)
    payload = default_llm_settings()
    if row and isinstance(row.value_json, dict):
        stored_default = normalize_provider(row.value_json.get("default_provider"))
        payload.update(
            {
                "default_provider": stored_default,
                "fallback_enabled": bool(row.value_json.get("fallback_enabled", True)),
                "fallback_order": normalize_fallback_order(
                    stored_default,
                    row.value_json.get("fallback_order") or [],
                ),
            }
        )
    payload["active_provider"] = payload["default_provider"]
    payload["providers"] = provider_statuses()
    return payload


def validate_llm_settings_update(payload: dict[str, Any]) -> dict[str, Any]:
    default_provider = normalize_provider(payload.get("default_provider"))
    fallback_enabled = bool(payload.get("fallback_enabled", True))
    fallback_order = normalize_fallback_order(default_provider, payload.get("fallback_order") or [])

    if not provider_configured(default_provider):
        missing = PROVIDER_KEY_ENV[default_provider]
        raise ValueError(f"{PROVIDER_LABELS[default_provider]} is selected but {missing} is not configured.")

    if fallback_enabled and not any(provider_configured(provider) for provider in fallback_order):
        raise ValueError("Automatic fallback is enabled, but none of the fallback providers have API keys.")

    return {
        "default_provider": default_provider,
        "fallback_enabled": fallback_enabled,
        "fallback_order": fallback_order,
    }


def save_llm_settings(db: Session, payload: dict[str, Any], user: User | None = None) -> dict[str, Any]:
    normalized = validate_llm_settings_update(payload)
    row = db.get(RuntimeSetting, LLM_SETTINGS_KEY)
    if row:
        row.value_json = normalized
        row.updated_by = user.username if user else None
        row.updated_at = datetime.utcnow()
    else:
        row = RuntimeSetting(
            key=LLM_SETTINGS_KEY,
            value_json=normalized,
            updated_by=user.username if user else None,
        )
        db.add(row)
    db.commit()
    return get_llm_settings(db)
