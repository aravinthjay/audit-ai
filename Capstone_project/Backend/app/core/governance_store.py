"""Persistence for governance/UI settings edited from the Settings page.

Values default to the environment-driven config and are overridden by a single
JSON row in ``runtime_settings`` (key ``governance``). This lets the UI's
"Save policy" button persist real changes without exposing secrets or requiring
an app restart.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RuntimeSetting, User

GOVERNANCE_SETTINGS_KEY = "governance"

# (field, coercer) for every editable governance setting.
_FIELDS: dict[str, type] = {
    "reasoning_model": str,
    "report_model": str,
    "auto_clear_threshold": float,
    "reviewer_threshold": float,
    "materiality": float,
    "segregation_of_duties": bool,
    "immutable_audit_log": bool,
    "debate_round_cap": int,
    "api_key_vault": str,
    "theme": str,
    "display_currency": str,
    "notifications": bool,
    "audit_retention_years": int,
    "ip_allowlist": bool,
    "estimated_agent_run_cost_usd": float,
}

_ALLOWED_THEMES = {"system", "light", "dark"}


def default_governance_settings() -> dict[str, Any]:
    """Environment-driven defaults, used when nothing is persisted yet."""
    return {
        "reasoning_model": settings.CLAUDE_MODEL_REASONING,
        "report_model": settings.CLAUDE_MODEL_LIGHTWEIGHT,
        "auto_clear_threshold": settings.DEFAULT_CONFIDENCE_THRESHOLD,
        "reviewer_threshold": settings.DEFAULT_ESCALATION_THRESHOLD,
        "materiality": settings.DEFAULT_MATERIALITY_THRESHOLD,
        "segregation_of_duties": settings.ENFORCE_SEGREGATION_OF_DUTIES,
        "immutable_audit_log": settings.IMMUTABLE_AUDIT_LOG_REQUIRED,
        "debate_round_cap": settings.MAX_DEBATE_ROUNDS,
        "api_key_vault": settings.API_KEY_VAULT_NAME,
        "theme": settings.UI_THEME,
        "display_currency": settings.DISPLAY_CURRENCY,
        "notifications": settings.NOTIFICATIONS_ENABLED,
        "audit_retention_years": settings.AUDIT_RETENTION_YEARS,
        "ip_allowlist": settings.IP_ALLOWLIST_ENABLED,
        "estimated_agent_run_cost_usd": settings.ESTIMATED_AGENT_RUN_COST_USD,
    }


def get_governance_settings(db: Session) -> dict[str, Any]:
    """Defaults merged with any persisted overrides."""
    payload = default_governance_settings()
    row = db.get(RuntimeSetting, GOVERNANCE_SETTINGS_KEY)
    if row and isinstance(row.value_json, dict):
        for key in _FIELDS:
            if key in row.value_json and row.value_json[key] is not None:
                payload[key] = row.value_json[key]
    return payload


def _coerce(key: str, value: Any) -> Any:
    caster = _FIELDS[key]
    if caster is bool:
        return bool(value)
    return caster(value)


def validate_governance_update(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce and range-check an incoming update; raise ValueError on bad input."""
    normalized = default_governance_settings()
    for key in _FIELDS:
        if key in payload and payload[key] is not None:
            try:
                normalized[key] = _coerce(key, payload[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid value for '{key}': {payload[key]!r}") from exc

    if normalized["theme"] not in _ALLOWED_THEMES:
        raise ValueError("theme must be one of: system, light, dark.")
    if len(str(normalized["display_currency"])) != 3:
        raise ValueError("display_currency must be a 3-letter code.")
    if not 0.0 <= normalized["auto_clear_threshold"] <= 1.0:
        raise ValueError("auto_clear_threshold must be between 0 and 1.")
    if not 0.0 <= normalized["reviewer_threshold"] <= 1.0:
        raise ValueError("reviewer_threshold must be between 0 and 1.")
    if normalized["debate_round_cap"] < 1:
        raise ValueError("debate_round_cap must be at least 1.")
    if normalized["audit_retention_years"] < 1:
        raise ValueError("audit_retention_years must be at least 1.")
    if normalized["materiality"] < 0:
        raise ValueError("materiality cannot be negative.")

    normalized["display_currency"] = str(normalized["display_currency"]).upper()
    return normalized


def save_governance_settings(
    db: Session,
    payload: dict[str, Any],
    user: User | None = None,
) -> dict[str, Any]:
    normalized = validate_governance_update(payload)
    row = db.get(RuntimeSetting, GOVERNANCE_SETTINGS_KEY)
    if row:
        row.value_json = normalized
        row.updated_by = user.username if user else None
        row.updated_at = datetime.utcnow()
    else:
        row = RuntimeSetting(
            key=GOVERNANCE_SETTINGS_KEY,
            value_json=normalized,
            updated_by=user.username if user else None,
        )
        db.add(row)
    db.commit()
    return get_governance_settings(db)
