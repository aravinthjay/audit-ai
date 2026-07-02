"""Runtime governance settings exposed to the UI."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.security import get_current_user
from app.db.session import get_db_session
from app.llm.settings_store import get_llm_settings, provider_statuses, save_llm_settings
from app.schemas import AppSettingsOut, LLMProviderStatusOut, LLMSettingsOut, LLMSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsOut)
async def get_settings(user=Depends(get_current_user)):
    """Return non-secret runtime settings that drive UI policy controls."""
    del user
    return AppSettingsOut(
        reasoning_model=app_settings.CLAUDE_MODEL_REASONING,
        report_model=app_settings.CLAUDE_MODEL_LIGHTWEIGHT,
        auto_clear_threshold=app_settings.DEFAULT_CONFIDENCE_THRESHOLD,
        reviewer_threshold=app_settings.DEFAULT_ESCALATION_THRESHOLD,
        materiality=app_settings.DEFAULT_MATERIALITY_THRESHOLD,
        segregation_of_duties=app_settings.ENFORCE_SEGREGATION_OF_DUTIES,
        immutable_audit_log=app_settings.IMMUTABLE_AUDIT_LOG_REQUIRED,
        debate_round_cap=app_settings.MAX_DEBATE_ROUNDS,
        api_key_vault=app_settings.API_KEY_VAULT_NAME,
        theme=app_settings.UI_THEME,
        display_currency=app_settings.DISPLAY_CURRENCY,
        notifications=app_settings.NOTIFICATIONS_ENABLED,
        audit_retention_years=app_settings.AUDIT_RETENTION_YEARS,
        ip_allowlist=app_settings.IP_ALLOWLIST_ENABLED,
        estimated_agent_run_cost_usd=app_settings.ESTIMATED_AGENT_RUN_COST_USD,
    )


@router.get("/llm", response_model=LLMSettingsOut)
async def get_llm_runtime_settings(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Return persisted LLM routing settings and provider key status."""
    del user
    return get_llm_settings(db)


@router.put("/llm", response_model=LLMSettingsOut)
async def update_llm_runtime_settings(
    payload: LLMSettingsUpdate,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Persist LLM routing settings without exposing provider secrets."""
    try:
        return save_llm_settings(db, payload.model_dump(), user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/llm/providers", response_model=list[LLMProviderStatusOut])
async def get_llm_providers(user=Depends(get_current_user)):
    """Return supported LLM providers and whether each API key is configured."""
    del user
    return provider_statuses()
