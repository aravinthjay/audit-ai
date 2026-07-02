"""Claim evidence verification routes.

The product currently stores uploaded claims as investigations. These routes
provide claim-named API aliases while persisting against the investigation id.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import Investigation, ThirdPartyEvidenceVerification
from app.db.session import get_db_session
from app.evidence_verification import EvidenceVerificationService
from app.realtime.websocket_manager import VerificationEvent, connection_manager
from app.schemas import (
    ClaimEvidencePreviewRequest,
    ClaimEvidenceVerificationOut,
    ClaimEvidenceVerifyRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/claims", tags=["claims"])


def _service() -> EvidenceVerificationService:
    return EvidenceVerificationService()


def _actor_name(user, fallback: str = "system") -> str:
    return getattr(user, "username", None) or fallback


async def record_evidence_verification_event(
    verification: ThirdPartyEvidenceVerification,
    actor: str,
) -> None:
    """Write audit/realtime side effects for a verification attempt."""

    details = {
        "verification_id": verification.id,
        "category": verification.category,
        "claimed_amount": verification.claimed_amount,
        "fetched_amount": verification.fetched_amount,
        "difference_amount": verification.difference_amount,
        "difference_percentage": verification.difference_percentage,
        "tolerance_percentage": verification.tolerance_percentage,
        "provider_name": verification.provider_name,
        "provider_reference_id": verification.provider_reference_id,
        "verification_status": verification.verification_status,
        "confidence_score": verification.confidence_score,
        "reason": verification.reason,
    }

    try:
        from app.audit.eventstore import log_verification_completed

        await log_verification_completed(verification.claim_id, actor=actor, details=details)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Evidence verification audit write failed for %s: %s",
            verification.claim_id,
            exc,
        )

    try:
        await connection_manager.broadcast(
            verification.claim_id,
            VerificationEvent(
                verification.claim_id,
                verification.id,
                verification.verification_status,
                metadata=details,
            ).to_dict(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Evidence verification websocket broadcast failed for %s: %s",
            verification.claim_id,
            exc,
        )


@router.post("/verify-preview", response_model=ClaimEvidenceVerificationOut)
async def verify_claim_preview(
    payload: ClaimEvidencePreviewRequest,
    user=Depends(get_current_user),
):
    del user
    result = _service().verify_preview(payload.model_dump())
    return ClaimEvidenceVerificationOut.model_validate(result)


@router.post(
    "/{claim_id}/verify-evidence",
    response_model=ClaimEvidenceVerificationOut,
    status_code=status.HTTP_201_CREATED,
)
async def verify_claim_evidence(
    claim_id: str,
    payload: ClaimEvidenceVerifyRequest | None = None,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    investigation = db.get(Investigation, claim_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Claim not found")

    verification = _service().verify_investigation(
        db,
        investigation,
        payload.model_dump(exclude_none=True) if payload else None,
    )
    await record_evidence_verification_event(verification, actor=_actor_name(user))
    return verification


@router.get("/{claim_id}/verification", response_model=ClaimEvidenceVerificationOut)
async def get_claim_verification(
    claim_id: str,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    del user
    if not db.get(Investigation, claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")

    verification = _service().get_latest(db, claim_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Claim verification not found")
    return verification
