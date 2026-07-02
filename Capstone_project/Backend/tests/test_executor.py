"""End-to-end executor test using deterministic stub agents (no LLM)."""

import asyncio

from app.agents.executor import InvestigationExecutor
from app.core.config import settings
from app.db.models import (
    DebateTranscript,
    EvidenceArtifact,
    Investigation,
    InvestigationStatus,
    ReviewQueueItem,
    VerificationClaim,
)


def test_executor_runs_full_pipeline(db):
    investigation = Investigation(
        transaction_id="TXN-EXEC",
        vendor="Gamma LLC",
        category="software",
        amount=120000.0,
        materiality=50000.0,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    inv_id = investigation.id

    executor = InvestigationExecutor(db)
    result = asyncio.run(executor.execute_investigation(inv_id))
    assert result["status"] == "review"
    assert result["attempts"] == settings.MAX_VERIFICATION_RETRIES + 1

    db.expire_all()
    refreshed = db.get(Investigation, inv_id)
    assert refreshed.status == InvestigationStatus.HUMAN_REVIEW
    assert refreshed.completed_at is None
    assert refreshed.reviewer
    assert refreshed.confidence > 0

    queue_item = db.query(ReviewQueueItem).filter_by(investigation_id=inv_id).one()
    assert queue_item.status == "pending"
    assert queue_item.assigned_to in {"reviewer_pool", "engagement_partner"}
    assert queue_item.notes

    transcripts = (
        db.query(DebateTranscript)
        .filter_by(investigation_id=inv_id)
        .order_by(DebateTranscript.round.asc(), DebateTranscript.created_at.asc())
        .all()
    )
    messages_per_attempt = (settings.MAX_DEBATE_ROUNDS * 2) + 1
    assert len(transcripts) == messages_per_attempt * result["attempts"]
    assert any(row.speaker == "adjudicator" for row in transcripts)
    assert all(row.token_count > 0 for row in transcripts)

    challenger_messages = [row.message for row in transcripts if row.speaker == "challenger"]
    assert len(challenger_messages) >= 2
    assert challenger_messages[0] != challenger_messages[1]
    assert any("vendor registry" in row.message.lower() for row in transcripts)

    evidence_sources = {
        row.source for row in db.query(EvidenceArtifact).filter_by(investigation_id=inv_id).all()
    }
    assert {"ledger_row", "intake_prefilter", "policy_kb", "vendor_registry"}.issubset(
        evidence_sources
    )

    claims = db.query(VerificationClaim).filter_by(investigation_id=inv_id).all()
    assert len(claims) >= 2
    assert any(not claim.is_grounded for claim in claims)
    assert any(claim.is_grounded for claim in claims)


def test_executor_marks_failed_on_missing_investigation(db):
    executor = InvestigationExecutor(db)
    result = asyncio.run(executor.execute_investigation("missing-id"))
    assert result["status"] == "failed"
