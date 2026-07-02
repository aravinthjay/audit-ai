"""Report routes - report artifacts derived from completed investigations."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import Investigation, InvestigationStatus, RiskLevel
from app.db.session import get_db_session

router = APIRouter(prefix="/reports", tags=["reports"])

_STATUS_TO_REPORT = {
    InvestigationStatus.REPORT_READY.value: "ready",
    InvestigationStatus.CLOSED.value: "approved",
    InvestigationStatus.HUMAN_REVIEW.value: "draft",
    InvestigationStatus.VERIFICATION.value: "draft",
}


def _status_value(investigation: Investigation) -> str:
    raw = investigation.status
    return raw.value if hasattr(raw, "value") else str(raw)


def _risk_value(investigation: Investigation) -> str:
    raw = investigation.risk
    return (raw.value if hasattr(raw, "value") else str(raw)) if raw else "medium"


def _audience(risk: str) -> str:
    if risk in (RiskLevel.CRITICAL.value, RiskLevel.HIGH.value):
        return "Partner"
    if risk == RiskLevel.MEDIUM.value:
        return "Engagement team"
    return "Audit committee"


@router.get("")
async def list_reports(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Report artifacts for investigations that have reached a reportable stage."""
    reportable = {
        InvestigationStatus.VERIFICATION.value,
        InvestigationStatus.HUMAN_REVIEW.value,
        InvestigationStatus.REPORT_READY.value,
        InvestigationStatus.CLOSED.value,
    }
    rows = (
        db.query(Investigation)
        .order_by(Investigation.updated_at.desc(), Investigation.created_at.desc())
        .all()
    )
    reports = []
    for inv in rows:
        status_value = _status_value(inv)
        if status_value not in reportable:
            continue
        risk = _risk_value(inv)
        report_status = _STATUS_TO_REPORT.get(status_value, "draft")
        updated = inv.completed_at or inv.updated_at or inv.created_at
        reports.append(
            {
                "id": f"RPT-{inv.id}",
                "investigation_id": inv.id,
                "title": f"{inv.vendor} - {inv.category} ({inv.transaction_id})",
                "status": report_status,
                "updated_at": updated.isoformat() if updated else None,
                "confidence": round(float(inv.confidence or 0.0), 4),
                "audience": _audience(risk),
                "risk_verdict": risk,
                "sections": [
                    "Executive summary",
                    "Evidence",
                    "Debate transcript",
                    "Verification",
                    "Decision & audit trail",
                ],
                "executive_summary": (
                    inv.description
                    or f"{inv.vendor} transaction {inv.transaction_id} for "
                    f"{inv.amount:,.2f} was assessed {risk} risk."
                ),
                "human_decision": (
                    "Approved and closed"
                    if status_value == InvestigationStatus.CLOSED.value
                    else "Pending human review"
                    if status_value == InvestigationStatus.HUMAN_REVIEW.value
                    else "Auto-cleared - reviewer confirmation pending"
                ),
                "reviewer_signature": inv.reviewer or "Unsigned",
            }
        )
    return reports
