"""Global audit routes - recent immutable audit events across all cases."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import AuditLog
from app.db.session import get_db_session

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/recent")
async def recent_audit_events(
    limit: int = 200,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Most recent audit events across every investigation.

    Shapes each row like the per-case audit endpoint so the same frontend
    mapper works for the global audit-log view.
    """
    limit = max(1, min(limit, 500))
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.sequence.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "type": r.event_type,
            "data": r.details,
            "hash": r.hash,
            "prev_hash": r.prev_hash,
            "sequence": r.sequence,
        }
        for r in rows
    ]
