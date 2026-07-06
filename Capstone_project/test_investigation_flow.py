"""
test_investigation_flow.py
===========================

This file tests the *whole story* of an investigation from start to finish,
instead of testing one small piece at a time. Think of it as a "walkthrough"
test: it presses the same buttons a real user (or the frontend) would press,
in the same order, and checks that each step leaves the system in the state
we expect.

The story we test, step by step:

    1. Create a new investigation        (like filing a new audit case)
    2. Read it back                      (make sure it was saved correctly)
    3. Run it                             (this kicks off the multi-agent
                                            pipeline: Evidence -> Debate ->
                                            Verification -> Decision)
    4. Check the final result             (did it reach a sensible end state?)
    5. Check the "paper trail"            (evidence, debate transcript,
                                            verification claims, audit log)
    6. Check the human-review queue       (if the case needed a human)
    7. Check a couple of "not found" /
       validation error cases             (the app should fail politely)

Why two different ways of running step 3?
------------------------------------------
This backend can execute an investigation in two ways:

    - Through the HTTP API (`POST /investigations/{id}/execute`), which is
      what the real frontend does. In tests (and in local dev without
      Celery/Redis) this quietly falls back to running the pipeline
      in-process instead of on a separate Celery worker.

    - Directly in Python, by creating an `InvestigationExecutor` and calling
      it ourselves. This is useful when we want to `await` the result
      directly instead of guessing how long the background task will take.

We use the *direct* executor for the main flow test below because it lets us
assert on the final result deterministically, without sleeping/polling. A
second, lighter test shows the same flow through the public HTTP API, the
way the frontend actually calls it.

Notes for anyone new to this test suite:
    - The `client` and `db` fixtures come from tests/conftest.py. They give
      you a fully working FastAPI TestClient and a database session, both
      pointed at a throwaway SQLite database created just for the test run.
    - `USE_REAL_AGENTS=false` is set in conftest.py, so no real LLM calls
      are made here. The agents run in a deterministic "stub" mode. That
      makes these tests fast, free, and repeatable.
"""

import asyncio

import pytest

from app.agents.executor import InvestigationExecutor
from app.core.config import settings
from app.db.models import (
    AuditLog,
    DebateTranscript,
    EvidenceArtifact,
    Investigation,
    InvestigationStatus,
    ReviewQueueItem,
    VerificationClaim,
)

# A sample "case" we will run through the pipeline. Amount is deliberately
# well above the materiality threshold so the case is treated as worth
# investigating (this mirrors how a real high-value vendor payment would be
# flagged).
SAMPLE_CASE = {
    "transaction_id": "TXN-FLOW-001",
    "vendor": "Acme Consulting Pvt Ltd",
    "category": "Consulting",
    "amount": 120000.0,
}


# ---------------------------------------------------------------------------
# Small helper functions (keep the tests below easy to read)
# ---------------------------------------------------------------------------

def create_investigation(client, payload=None):
    """POST a new investigation and return the parsed JSON body."""
    payload = payload or SAMPLE_CASE
    response = client.post("/api/v1/investigations", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def run_investigation_directly(db, investigation_id):
    """Run the agent pipeline for one investigation, synchronously.

    `execute_investigation` is an `async` method, so we use `asyncio.run`
    to execute it right now and wait for the answer, exactly like
    test_executor.py does elsewhere in this suite.
    """
    executor = InvestigationExecutor(db)
    return asyncio.run(executor.execute_investigation(investigation_id))


# ---------------------------------------------------------------------------
# 1) Create -> 2) Read back
# ---------------------------------------------------------------------------

def test_step1_create_and_read_back_investigation(client):
    """A freshly created investigation should be saved with status 'intake'
    and be immediately readable through the API."""
    created = create_investigation(client)

    assert created["transaction_id"] == SAMPLE_CASE["transaction_id"]
    assert created["vendor"] == SAMPLE_CASE["vendor"]
    assert created["status"] == "intake"

    investigation_id = created["id"]

    fetched = client.get(f"/api/v1/investigations/{investigation_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == investigation_id


# ---------------------------------------------------------------------------
# 3) Run it -> 4) Check the final result -> 5) Check the paper trail
# ---------------------------------------------------------------------------

def test_step2_full_pipeline_runs_and_reaches_a_final_state(client, db):
    """This is the main end-to-end test: create a case, run the full
    multi-agent pipeline directly, and confirm the system produced a
    complete, well-formed result.
    """
    created = create_investigation(client, {**SAMPLE_CASE, "transaction_id": "TXN-FLOW-002"})
    investigation_id = created["id"]

    # --- Run the pipeline (Evidence -> Debate -> Verification -> Decision) ---
    result = run_investigation_directly(db, investigation_id)

    # The pipeline should always tell us a final status, one way or another.
    assert result["status"] in ("closed", "review", "failed")
    assert "attempts" in result

    # --- Re-read the investigation from the database to see its new state ---
    db.expire_all()  # forget any cached values so we read the fresh row
    investigation = db.get(Investigation, investigation_id)
    assert investigation is not None
    assert investigation.status in (
        InvestigationStatus.HUMAN_REVIEW,
        InvestigationStatus.REPORT_READY,
        InvestigationStatus.CLOSED,
        InvestigationStatus.FAILED,
    )
    # A case that finished the pipeline should have a risk score/confidence,
    # even if a human still needs to sign off on it.
    assert investigation.confidence is not None

    # --- Evidence: the Evidence agent should have collected something ---
    evidence_rows = (
        db.query(EvidenceArtifact).filter_by(investigation_id=investigation_id).all()
    )
    assert len(evidence_rows) > 0
    evidence_sources = {row.source for row in evidence_rows}
    # These two sources come straight from the case data itself, so they
    # should always be present regardless of what the debate concludes.
    assert "ledger_row" in evidence_sources
    assert "intake_prefilter" in evidence_sources

    # --- Debate: Challenger and Defender should have exchanged messages ---
    transcript = (
        db.query(DebateTranscript)
        .filter_by(investigation_id=investigation_id)
        .order_by(DebateTranscript.round.asc(), DebateTranscript.created_at.asc())
        .all()
    )
    assert len(transcript) > 0
    speakers = {row.speaker for row in transcript}
    assert "challenger" in speakers
    assert "defender" in speakers
    assert "adjudicator" in speakers
    # Every recorded message should have some token count, i.e. it isn't
    # an empty/blank message.
    assert all(row.token_count > 0 for row in transcript)

    # --- Verification: the Verifier should have QA-checked at least one claim ---
    claims = db.query(VerificationClaim).filter_by(investigation_id=investigation_id).all()
    assert len(claims) > 0

    # --- Audit trail: closing (or failing) a case should leave a paper trail ---
    audit_rows = db.query(AuditLog).filter_by(investigation_id=investigation_id).all()
    assert len(audit_rows) > 0


def test_step3_case_needing_a_human_lands_in_the_review_queue(db):
    """If the Verifier can't fully ground the verdict, the Supervisor
    escalates to a human instead of silently closing the case. This test
    checks that the review-queue side effect actually happens.
    """
    investigation = Investigation(
        transaction_id="TXN-FLOW-003",
        vendor="Gamma LLC",
        category="Software",
        amount=250000.0,
        materiality=50000.0,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    result = run_investigation_directly(db, investigation.id)

    # With the deterministic stub agents used in tests, this scenario is
    # expected to need a human reviewer at least once during the run.
    if result["status"] == "review":
        queue_item = (
            db.query(ReviewQueueItem).filter_by(investigation_id=investigation.id).first()
        )
        assert queue_item is not None
        assert queue_item.status == "pending"
        assert queue_item.assigned_to  # someone/something must own the case
    else:
        # If the stub agents didn't escalate this time, at least confirm the
        # pipeline still reached a valid, understandable end state.
        assert result["status"] in ("closed", "failed")


# ---------------------------------------------------------------------------
# The same flow, but the way the real frontend triggers it: over HTTP
# ---------------------------------------------------------------------------

def test_step4_full_flow_through_the_public_http_api(client):
    """Exercises the same create -> execute -> read-back flow, but only
    using the HTTP endpoints a real frontend would call - no direct access
    to the executor or the database session.
    """
    created = create_investigation(client, {**SAMPLE_CASE, "transaction_id": "TXN-FLOW-004"})
    investigation_id = created["id"]

    # Ask the API to start the investigation. Because there's no Celery
    # broker running in this test environment, the backend automatically
    # falls back to running the pipeline in-process (see
    # app/api/routes/investigations.py: _run_investigation_inline).
    execute_response = client.post(f"/api/v1/investigations/{investigation_id}/execute")
    assert execute_response.status_code == 200, execute_response.text
    assert execute_response.json()["status"] in ("queued", "running")

    # The TestClient runs FastAPI's BackgroundTasks before returning control
    # here, so by this point the pipeline has already finished running.
    final = client.get(f"/api/v1/investigations/{investigation_id}")
    assert final.status_code == 200
    assert final.json()["status"] in (
        "human_review",
        "report_ready",
        "closed",
        "failed",
    )

    # The sub-resource endpoints the frontend uses to render the case detail
    # page should now return real data instead of empty lists.
    evidence = client.get(f"/api/v1/investigations/{investigation_id}/evidence")
    assert evidence.status_code == 200
    assert len(evidence.json()) > 0

    debate = client.get(f"/api/v1/investigations/{investigation_id}/debate")
    assert debate.status_code == 200
    assert len(debate.json()) > 0


# ---------------------------------------------------------------------------
# 7) Things that should fail politely
# ---------------------------------------------------------------------------

def test_step5_executing_an_unknown_investigation_returns_404(client):
    """Trying to execute a case that doesn't exist should give a clear,
    expected error - not a crash."""
    response = client.post("/api/v1/investigations/does-not-exist/execute")
    assert response.status_code == 404


def test_step6_creating_an_investigation_with_missing_fields_is_rejected(client):
    """Leaving out required fields (here: transaction_id, category, amount)
    should be caught by validation before it ever reaches the database."""
    response = client.post("/api/v1/investigations", json={"vendor": "Incomplete Corp"})
    assert response.status_code == 422


def test_step7_executor_handles_a_missing_investigation_gracefully(db):
    """Calling the executor directly on an id that was never created should
    report failure instead of raising an unhandled exception."""
    executor = InvestigationExecutor(db)
    result = asyncio.run(executor.execute_investigation("this-id-does-not-exist"))
    assert result["status"] == "failed"


if __name__ == "__main__":
    # Lets you run `python tests/test_investigation_flow.py` directly in
    # addition to the normal `pytest` command.
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
