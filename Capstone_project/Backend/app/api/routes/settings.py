"""Runtime governance settings exposed to the UI."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.governance_store import get_governance_settings, save_governance_settings
from app.core.security import get_current_user
from app.db.session import get_db_session
from app.llm.settings_store import get_llm_settings, provider_statuses, save_llm_settings
from app.schemas import (
    AppSettingsOut,
    AppSettingsUpdate,
    LLMProviderStatusOut,
    LLMSettingsOut,
    LLMSettingsUpdate,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsOut)
async def get_settings(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Return non-secret runtime settings that drive UI policy controls."""
    del user
    return AppSettingsOut(**get_governance_settings(db))


@router.put("", response_model=AppSettingsOut)
async def update_settings(
    payload: AppSettingsUpdate,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Persist edited governance settings from the Settings page."""
    try:
        saved = save_governance_settings(db, payload.model_dump(exclude_none=True), user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AppSettingsOut(**saved)


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
