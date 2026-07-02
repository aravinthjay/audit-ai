"""Human review queue + decision routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import Investigation, InvestigationStatus, ReviewQueueItem, RiskLevel
from app.db.session import get_db_session
from app.schemas import ReviewActionRequest, ReviewActionResponse, ReviewQueueOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["reviews"])


def _actor(request: ReviewActionRequest, user) -> str:
    if request.actor:
        return request.actor
    username = getattr(user, "username", None)
    return username or "system"


def _queue_name(assigned_to: str | None, risk: RiskLevel | None) -> str:
    if assigned_to == "engagement_partner" or risk == RiskLevel.CRITICAL:
        return "partner"
    return "reviewer"


def _priority_for(investigation: Investigation, assigned_to: str | None = None) -> int:
    if assigned_to == "engagement_partner" or investigation.risk == RiskLevel.CRITICAL:
        return 1
    if investigation.risk == RiskLevel.HIGH:
        return 2
    return 3


def _queue_out(item: ReviewQueueItem, investigation: Investigation) -> ReviewQueueOut:
    return ReviewQueueOut(
        id=item.id,
        investigation_id=investigation.id,
        title=f"{investigation.vendor} / {investigation.category}",
        risk=investigation.risk.value if investigation.risk else None,
        confidence=investigation.confidence or 0.0,
        due_at=investigation.due_at,
        queue=_queue_name(item.assigned_to, investigation.risk),
        status=item.status or "pending",
        assigned_to=item.assigned_to,
        priority=item.priority or _priority_for(investigation, item.assigned_to),
        notes=item.notes,
    )


def _upsert_pending_queue(
    db: Session,
    investigation: Investigation,
    assigned_to: str | None,
    priority: int | None = None,
    notes: str | None = None,
) -> ReviewQueueItem:
    item = (
        db.query(ReviewQueueItem)
        .filter(
            ReviewQueueItem.investigation_id == investigation.id,
            ReviewQueueItem.status == "pending",
        )
        .order_by(ReviewQueueItem.created_at.desc())
        .first()
    )
    if item is None:
        item = ReviewQueueItem(investigation_id=investigation.id)
        db.add(item)

    item.assigned_to = assigned_to
    item.priority = priority or _priority_for(investigation, assigned_to)
    item.status = "pending"
    item.notes = notes or item.notes or "Awaiting human review."
    item.completed_at = None
    item.updated_at = datetime.utcnow()
    return item


def _close_pending_queue(
    db: Session,
    investigation_id: str,
    status: str,
    actor: str,
    comment: str | None = None,
) -> None:
    rows = (
        db.query(ReviewQueueItem)
        .filter(
            ReviewQueueItem.investigation_id == investigation_id,
            ReviewQueueItem.status == "pending",
        )
        .all()
    )
    now = datetime.utcnow()
    note = f"{status} by {actor}"
    if comment:
        note = f"{note}: {comment}"
    for row in rows:
        row.status = status
        row.notes = note
        row.completed_at = now
        row.updated_at = now


@router.get("/queue", response_model=list[ReviewQueueOut])
async def review_queue(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Cases awaiting human review, backed by the review_queue table."""
    del user
    queued_rows = (
        db.query(ReviewQueueItem, Investigation)
        .join(Investigation, Investigation.id == ReviewQueueItem.investigation_id)
        .filter(
            ReviewQueueItem.status == "pending",
            Investigation.status == InvestigationStatus.HUMAN_REVIEW,
        )
        .order_by(
            ReviewQueueItem.priority.asc(),
            Investigation.due_at.is_(None),
            Investigation.due_at.asc(),
            ReviewQueueItem.created_at.asc(),
        )
        .all()
    )
    queued_ids = {investigation.id for _, investigation in queued_rows}

    # Backfill older cases that were marked for review before queue rows existed.
    fallback_query = (
        db.query(Investigation)
        .filter(Investigation.status == InvestigationStatus.HUMAN_REVIEW)
        .filter(Investigation.status != InvestigationStatus.CLOSED)
    )
    if queued_ids:
        fallback_query = fallback_query.filter(~Investigation.id.in_(queued_ids))

    backfilled: list[tuple[ReviewQueueItem, Investigation]] = []
    for investigation in fallback_query.all():
        assigned_to = investigation.reviewer or (
            "engagement_partner" if investigation.risk == RiskLevel.CRITICAL else "reviewer_pool"
        )
        item = _upsert_pending_queue(
            db,
            investigation,
            assigned_to=assigned_to,
            notes="Backfilled from investigation status/risk.",
        )
        investigation.status = InvestigationStatus.HUMAN_REVIEW
        investigation.reviewer = assigned_to
        backfilled.append((item, investigation))

    if backfilled:
        db.commit()
        for item, investigation in backfilled:
            db.refresh(item)
            db.refresh(investigation)

    rows = queued_rows + backfilled
    rows.sort(
        key=lambda pair: (
            pair[0].priority or _priority_for(pair[1], pair[0].assigned_to),
            pair[1].due_at or datetime.max,
            pair[0].created_at or datetime.max,
        )
    )
    return [_queue_out(item, investigation) for item, investigation in rows]


async def _log_review(investigation_id: str, event_type: str, actor: str, details: dict) -> None:
    try:
        from app.audit.eventstore import _log

        await _log(event_type, investigation_id, actor, details)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Audit log for review action failed: {exc}")


def _get_or_404(db: Session, investigation_id: str) -> Investigation:
    investigation = db.get(Investigation, investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


@router.post("/{investigation_id}/approve", response_model=ReviewActionResponse)
async def approve(
    investigation_id: str,
    payload: ReviewActionRequest = ReviewActionRequest(),
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    investigation = _get_or_404(db, investigation_id)
    actor = _actor(payload, user)
    investigation.status = InvestigationStatus.CLOSED
    investigation.reviewer = actor
    investigation.completed_at = datetime.utcnow()
    _close_pending_queue(db, investigation_id, "approved", actor, payload.comment)
    db.commit()
    await _log_review(investigation_id, "case_approved", actor, {"comment": payload.comment})
    return ReviewActionResponse(
        investigation_id=investigation_id,
        action="approve",
        status=investigation.status.value,
        message="Case approved and closed",
    )


@router.post("/{investigation_id}/reject", response_model=ReviewActionResponse)
async def reject(
    investigation_id: str,
    payload: ReviewActionRequest = ReviewActionRequest(),
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    investigation = _get_or_404(db, investigation_id)
    actor = _actor(payload, user)
    investigation.status = InvestigationStatus.CLOSED
    investigation.reviewer = actor
    investigation.completed_at = datetime.utcnow()
    _close_pending_queue(db, investigation_id, "rejected", actor, payload.comment)
    db.commit()
    await _log_review(investigation_id, "case_rejected", actor, {"comment": payload.comment})
    return ReviewActionResponse(
        investigation_id=investigation_id,
        action="reject",
        status=investigation.status.value,
        message="Case rejected and closed",
    )


@router.post("/{investigation_id}/request-evidence", response_model=ReviewActionResponse)
async def request_evidence(
    investigation_id: str,
    payload: ReviewActionRequest = ReviewActionRequest(),
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    investigation = _get_or_404(db, investigation_id)
    actor = _actor(payload, user)
    investigation.status = InvestigationStatus.COLLECTING_EVIDENCE
    investigation.reviewer = actor
    _close_pending_queue(db, investigation_id, "returned_to_evidence", actor, payload.comment)
    db.commit()
    await _log_review(
        investigation_id,
        "case_evidence_requested",
        actor,
        {"comment": payload.comment},
    )
    return ReviewActionResponse(
        investigation_id=investigation_id,
        action="request_evidence",
        status=investigation.status.value,
        message="Case returned to evidence collection",
    )


@router.post("/{investigation_id}/escalate", response_model=ReviewActionResponse)
async def escalate(
    investigation_id: str,
    payload: ReviewActionRequest = ReviewActionRequest(),
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    investigation = _get_or_404(db, investigation_id)
    actor = _actor(payload, user)
    investigation.status = InvestigationStatus.HUMAN_REVIEW
    investigation.risk = RiskLevel.CRITICAL
    investigation.reviewer = "engagement_partner"
    _upsert_pending_queue(
        db,
        investigation,
        assigned_to="engagement_partner",
        priority=1,
        notes=payload.comment or f"Escalated by {actor}.",
    )
    db.commit()
    await _log_review(investigation_id, "case_escalated", actor, {"comment": payload.comment})
    return ReviewActionResponse(
        investigation_id=investigation_id,
        action="escalate",
        status=investigation.status.value,
        message="Case escalated to partner review",
    )
