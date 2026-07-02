"""Agent telemetry routes backed by persisted investigation state."""

from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import (
    DebateTranscript,
    EvidenceArtifact,
    Investigation,
    InvestigationState,
    InvestigationStatus,
    ReviewQueueItem,
    VerificationClaim,
)
from app.db.session import get_db_session
from app.schemas import AgentHealthOut, PipelineStepOut

router = APIRouter(prefix="/agents", tags=["agents"])

_STATUS_ORDER = [
    InvestigationStatus.INTAKE.value,
    InvestigationStatus.COLLECTING_EVIDENCE.value,
    InvestigationStatus.AGENT_DEBATE.value,
    InvestigationStatus.VERIFICATION.value,
    InvestigationStatus.HUMAN_REVIEW.value,
    InvestigationStatus.REPORT_READY.value,
    InvestigationStatus.CLOSED.value,
]


def _status_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _stage_state(current: str, stage: str) -> str:
    if current == InvestigationStatus.FAILED.value:
        return "failed" if stage == InvestigationStatus.INTAKE.value else "idle"

    try:
        current_index = _STATUS_ORDER.index(current)
        stage_index = _STATUS_ORDER.index(stage)
    except ValueError:
        return "idle"

    if stage_index < current_index or current == InvestigationStatus.CLOSED.value:
        return "done"
    if stage_index == current_index:
        return "done" if current == InvestigationStatus.REPORT_READY.value else "running"
    return "idle"


def _count_rows(db: Session, model, investigation_id: str) -> int:
    return (
        db.query(func.count(model.id))
        .filter(model.investigation_id == investigation_id)
        .scalar()
        or 0
    )


def _token_count(db: Session, investigation_id: str, *speakers: str) -> int:
    lowered = {speaker.lower() for speaker in speakers}
    rows = (
        db.query(DebateTranscript.speaker, DebateTranscript.token_count)
        .filter(DebateTranscript.investigation_id == investigation_id)
        .all()
    )
    return sum(
        int(tokens or 0)
        for speaker, tokens in rows
        if str(speaker).lower() in lowered
    )


def _latest_attempt(db: Session, investigation_id: str) -> int:
    latest = (
        db.query(InvestigationState)
        .filter(InvestigationState.investigation_id == investigation_id)
        .order_by(InvestigationState.created_at.desc())
        .first()
    )
    if not latest or not isinstance(latest.state_json, dict):
        return 1
    try:
        return max(1, int(latest.state_json.get("attempt") or 1))
    except (TypeError, ValueError):
        return 1


def _health(
    label: str,
    counts: Counter[str],
    *,
    active: tuple[str, ...] = (),
    queued: tuple[str, ...] = (),
    review: tuple[str, ...] = (),
    total: int,
) -> AgentHealthOut:
    active_count = sum(counts.get(status, 0) for status in active)
    queued_count = sum(counts.get(status, 0) for status in queued)
    review_count = sum(counts.get(status, 0) for status in review)

    if active_count:
        state = "running"
        workload = f"{active_count} active"
    elif review_count:
        state = "review"
        workload = f"{review_count} in review"
    elif queued_count:
        state = "queued"
        workload = f"{queued_count} queued"
    elif total:
        state = "done"
        workload = "0 active"
    else:
        state = "idle"
        workload = "no cases"

    load_count = active_count + review_count + queued_count
    return AgentHealthOut(
        label=label,
        state=state,
        latency=workload,
        load=round(min(1.0, load_count / max(total, 1)), 4),
    )


@router.get("/health", response_model=list[AgentHealthOut])
async def agent_health(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Agent workload state derived from investigation statuses."""
    del user
    rows = (
        db.query(Investigation.status, func.count(Investigation.id))
        .group_by(Investigation.status)
        .all()
    )
    counts = Counter({_status_value(status): count for status, count in rows})
    total = sum(counts.values())

    return [
        _health(
            "Supervisor",
            counts,
            active=(
                InvestigationStatus.COLLECTING_EVIDENCE.value,
                InvestigationStatus.AGENT_DEBATE.value,
                InvestigationStatus.VERIFICATION.value,
            ),
            queued=(InvestigationStatus.INTAKE.value,),
            total=total,
        ),
        _health(
            "Evidence agent",
            counts,
            active=(InvestigationStatus.COLLECTING_EVIDENCE.value,),
            queued=(InvestigationStatus.INTAKE.value,),
            total=total,
        ),
        _health(
            "Challenger",
            counts,
            active=(InvestigationStatus.AGENT_DEBATE.value,),
            queued=(InvestigationStatus.COLLECTING_EVIDENCE.value,),
            total=total,
        ),
        _health(
            "Defender",
            counts,
            active=(InvestigationStatus.AGENT_DEBATE.value,),
            queued=(InvestigationStatus.COLLECTING_EVIDENCE.value,),
            total=total,
        ),
        _health(
            "Adjudicator",
            counts,
            active=(InvestigationStatus.AGENT_DEBATE.value,),
            queued=(InvestigationStatus.COLLECTING_EVIDENCE.value,),
            total=total,
        ),
        _health(
            "Verifier",
            counts,
            active=(InvestigationStatus.VERIFICATION.value,),
            queued=(InvestigationStatus.AGENT_DEBATE.value,),
            total=total,
        ),
        _health(
            "Confidence gate",
            counts,
            active=(InvestigationStatus.VERIFICATION.value,),
            review=(InvestigationStatus.HUMAN_REVIEW.value,),
            total=total,
        ),
        _health(
            "Human review",
            counts,
            review=(InvestigationStatus.HUMAN_REVIEW.value,),
            total=total,
        ),
    ]


@router.get("/workflow/{investigation_id}", response_model=list[PipelineStepOut])
async def agent_workflow(
    investigation_id: str,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Case-specific workflow state for the agent graph."""
    del user
    investigation = db.get(Investigation, investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    current = _status_value(investigation.status)
    attempt = _latest_attempt(db, investigation_id)
    evidence_count = _count_rows(db, EvidenceArtifact, investigation_id)
    debate_count = _count_rows(db, DebateTranscript, investigation_id)
    verification_count = _count_rows(db, VerificationClaim, investigation_id)
    review_count = _count_rows(db, ReviewQueueItem, investigation_id)
    updated = investigation.updated_at or investigation.created_at or datetime.utcnow()
    updated_label = f"updated {updated.isoformat()}"
    risk = _status_value(investigation.risk) if investigation.risk else "medium"

    stages = [
        {
            "id": "intake",
            "role": "Supervisor",
            "status": InvestigationStatus.INTAKE.value,
            "detail": (
                f"Case {investigation.transaction_id} is registered for "
                f"{investigation.vendor}."
            ),
            "expanded_detail": (
                investigation.description
                or "No case description has been recorded."
            ),
            "token_usage": 0,
        },
        {
            "id": "evidence",
            "role": "Evidence agent",
            "status": InvestigationStatus.COLLECTING_EVIDENCE.value,
            "detail": f"{evidence_count} evidence artifact(s) persisted.",
            "expanded_detail": "Evidence artifacts are read from the investigation evidence table.",
            "token_usage": 0,
        },
        {
            "id": "challenger",
            "role": "Challenger",
            "status": InvestigationStatus.AGENT_DEBATE.value,
            "detail": f"{debate_count} debate transcript message(s) recorded.",
            "expanded_detail": "Challenger messages are read from the debate transcript table.",
            "token_usage": _token_count(db, investigation_id, "challenger"),
        },
        {
            "id": "defender",
            "role": "Defender",
            "status": InvestigationStatus.AGENT_DEBATE.value,
            "detail": f"{debate_count} debate transcript message(s) recorded.",
            "expanded_detail": "Defender messages are read from the debate transcript table.",
            "token_usage": _token_count(db, investigation_id, "defender"),
        },
        {
            "id": "adjudicator",
            "role": "Adjudicator",
            "status": InvestigationStatus.AGENT_DEBATE.value,
            "detail": (
                f"Current risk: {risk}; "
                f"confidence {float(investigation.confidence or 0):.0%}."
            ),
            "expanded_detail": "Risk and confidence are read from the investigation record.",
            "token_usage": _token_count(db, investigation_id, "adjudicator"),
            "confidence": float(investigation.confidence or 0),
        },
        {
            "id": "verifier",
            "role": "Verifier",
            "status": InvestigationStatus.VERIFICATION.value,
            "detail": f"{verification_count} verification claim(s) persisted.",
            "expanded_detail": "Verification claims are read from the verification table.",
            "token_usage": 0,
        },
        {
            "id": "review",
            "role": "Human review",
            "status": InvestigationStatus.HUMAN_REVIEW.value,
            "detail": (
                f"Assigned to {investigation.reviewer}."
                if investigation.reviewer
                else f"{review_count} review queue item(s) recorded."
            ),
            "expanded_detail": (
                "Review status is read from the investigation and review queue tables."
            ),
            "token_usage": 0,
        },
        {
            "id": "report",
            "role": "Report",
            "status": InvestigationStatus.REPORT_READY.value,
            "detail": "Report readiness is derived from the investigation status.",
            "expanded_detail": (
                "Report artifacts are derived from reportable investigation records."
            ),
            "token_usage": 0,
        },
        {
            "id": "audit",
            "role": "Audit log",
            "status": InvestigationStatus.REPORT_READY.value,
            "detail": "Audit trail is loaded through the audit endpoints.",
            "expanded_detail": (
                "Audit events are persisted in EventStoreDB or the PostgreSQL "
                "hash-chain fallback."
            ),
            "token_usage": 0,
        },
    ]

    return [
        PipelineStepOut(
            id=stage["id"],
            role=stage["role"],
            state=_stage_state(current, stage["status"]),
            detail=stage["detail"],
            latency=updated_label,
            confidence=stage.get("confidence"),
            token_usage=stage["token_usage"],
            cost=0.0,
            attempt=attempt,
            expanded_detail=stage["expanded_detail"],
        )
        for stage in stages
    ]
