"""RAGAS evaluation routes.

Exposes the RAGAS metric catalog and a computed evaluation summary for the
/evaluation dashboard. Replaces the former A/B (single-prompt vs. crew) harness.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import Investigation
from app.db.session import get_db_session
from app.evaluation.ragas import compute_ragas_summary, metric_catalog
from app.schemas import EvaluationSummaryOut, RagasMetricOut

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/summary", response_model=EvaluationSummaryOut)
async def evaluation_summary(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """RAGAS scores derived from stored investigation telemetry."""
    return compute_ragas_summary(db)


@router.get("/case/{investigation_id}", response_model=EvaluationSummaryOut)
async def evaluation_for_case(
    investigation_id: str,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """RAGAS scores scoped to a single investigation."""
    del user
    exists = db.query(Investigation.id).filter(Investigation.id == investigation_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return compute_ragas_summary(db, investigation_id=investigation_id)


@router.get("/metrics", response_model=list[RagasMetricOut])
async def evaluation_metrics(
    user=Depends(get_current_user),
):
    """The canonical RAGAS metric catalog (definitions + targets)."""
    return metric_catalog()
