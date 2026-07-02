"""Tests for stats, sub-resource, review, and auth endpoints."""

from app.core.config import settings
from app.db.models import (
    AuditLog,
    DebateTranscript,
    EvidenceArtifact,
    Investigation,
    InvestigationState,
    InvestigationStatus,
    LLMCallLog,
    ReviewQueueItem,
    RuntimeSetting,
    ThirdPartyEvidenceVerification,
    VerificationClaim,
)


def _create(client, txn="TXN-EP", amount=80000.0):
    r = client.post(
        "/api/v1/investigations",
        json={"transaction_id": txn, "vendor": "Acme", "category": "consulting", "amount": amount},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_stats_summary(client):
    _create(client, txn="TXN-STATS")
    r = client.get("/api/v1/investigations/stats/summary")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert "by_risk" in body and "by_status" in body
    assert body["by_status"].get("intake", 0) >= 1


def test_subresources_empty_for_new_case(client):
    inv_id = _create(client, txn="TXN-SUB")
    for sub in ("debate", "evidence", "verification", "audit"):
        r = client.get(f"/api/v1/investigations/{inv_id}/{sub}")
        assert r.status_code == 200, (sub, r.text)
        assert isinstance(r.json(), list)


def test_runtime_settings_endpoint_exposes_no_secrets(client):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["materiality"] == settings.DEFAULT_MATERIALITY_THRESHOLD
    assert body["estimated_agent_run_cost_usd"] == settings.ESTIMATED_AGENT_RUN_COST_USD
    assert "secret_key" not in body
    assert "default_admin_password" not in body


def test_llm_settings_endpoint_exposes_provider_status_without_keys(client):
    r = client.get("/api/v1/settings/llm")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["default_provider"] in ("anthropic", "groq", "openai")
    assert any(provider["id"] == "anthropic" for provider in body["providers"])
    assert "sk-" not in str(body).lower()
    assert "secret" not in str(body).lower()


def test_llm_settings_update_validates_missing_provider_key(client, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    r = client.put(
        "/api/v1/settings/llm",
        json={"default_provider": "openai", "fallback_enabled": False, "fallback_order": []},
    )
    assert r.status_code == 400
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_request_logging_populates_analytics(client):
    r = client.get("/api/v1/investigations?limit=1", headers={"x-request-id": "req-test-1"})
    assert r.status_code == 200, r.text
    assert r.headers["x-request-id"] == "req-test-1"

    analytics = client.get("/api/v1/analytics/requests")
    assert analytics.status_code == 200, analytics.text
    body = analytics.json()
    assert body["total_requests"] >= 1
    assert body["avg_duration_ms"] >= 0
    assert body["by_status"].get("200", 0) >= 1
    assert any(item["path"] == "/api/v1/investigations" for item in body["top_paths"])


def test_llm_analytics_endpoints_aggregate_costs(client, db):
    db.query(LLMCallLog).filter(LLMCallLog.request_type == "endpoint-test").delete()
    db.query(RuntimeSetting).filter(RuntimeSetting.key == "llm").delete()
    db.add_all(
        [
            LLMCallLog(
                provider_name="anthropic",
                model_name="claude-3-5-sonnet-20241022",
                request_type="endpoint-test",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=0.001,
                latency_ms=120,
                success=True,
                fallback_used=False,
                model_tier="reasoning",
            ),
            LLMCallLog(
                provider_name="groq",
                model_name="llama-3.3-70b-versatile",
                request_type="endpoint-test",
                prompt_tokens=80,
                completion_tokens=20,
                total_tokens=100,
                estimated_cost_usd=0.0001,
                latency_ms=45,
                success=True,
                fallback_used=True,
                fallback_provider="groq",
                model_tier="reasoning",
            ),
        ]
    )
    db.commit()

    summary = client.get("/api/v1/analytics/llm/summary?request_type=endpoint-test")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["total_tokens"] == 250
    assert body["fallback_calls"] == 1
    assert body["successful_calls"] == 2

    by_provider = client.get("/api/v1/analytics/llm/by-provider?request_type=endpoint-test")
    assert by_provider.status_code == 200, by_provider.text
    assert {row["provider_name"] for row in by_provider.json()} == {"anthropic", "groq"}

    recent = client.get("/api/v1/analytics/llm/recent-calls?request_type=endpoint-test")
    assert recent.status_code == 200
    assert len(recent.json()) >= 2


def test_agent_health_and_workflow_routes_use_persisted_state(client, db):
    inv_id = _create(client, txn="TXN-AGENTS")
    investigation = db.get(Investigation, inv_id)
    investigation.status = InvestigationStatus.AGENT_DEBATE
    investigation.confidence = 0.84
    db.add_all(
        [
            EvidenceArtifact(investigation_id=inv_id, source="ledger", content="ledger fact"),
            DebateTranscript(
                investigation_id=inv_id,
                round=1,
                speaker="challenger",
                message="challenge",
                token_count=5,
            ),
            DebateTranscript(
                investigation_id=inv_id,
                round=1,
                speaker="defender",
                message="defense",
                token_count=7,
            ),
        ]
    )
    db.commit()

    health = client.get("/api/v1/agents/health")
    assert health.status_code == 200, health.text
    assert any(item["label"] == "Supervisor" for item in health.json())
    assert any(item["state"] == "running" for item in health.json())

    workflow = client.get(f"/api/v1/agents/workflow/{inv_id}")
    assert workflow.status_code == 200, workflow.text
    body = workflow.json()
    challenger = next(item for item in body if item["id"] == "challenger")
    adjudicator = next(item for item in body if item["id"] == "adjudicator")
    assert challenger["token_usage"] == 5
    assert adjudicator["confidence"] == 0.84


def test_intake_summary_route_uses_imported_cases(client, db):
    inv_id = _create(client, txn="TXN-INTAKE-SUMMARY")
    investigation = db.get(Investigation, inv_id)
    investigation.owner = "intake"
    investigation.description = (
        "Created from intake file ledger.csv. "
        "Rules fired: materiality, unknown vendor. "
        "Source account: consulting."
    )
    investigation.flags = ["materiality", "unknown vendor"]
    db.commit()

    r = client.get("/api/v1/intake/summary")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["file_name"] == "ledger.csv"
    assert body["rows_ingested"] >= 1
    assert body["flagged_rows"][0]["txn_id"] == "TXN-INTAKE-SUMMARY"
    assert any(item["rule"].startswith("Materiality >=") for item in body["rule_stats"])

    investigation.owner = "summary_test"
    db.commit()


def test_delete_imported_investigations_removes_cases_and_generated_data(client, db):
    imported_id = _create(client, txn="TXN-IMPORTED")
    manual_id = _create(client, txn="TXN-MANUAL")
    imported = db.get(Investigation, imported_id)
    imported.owner = "intake"
    db.add_all(
        [
            EvidenceArtifact(investigation_id=imported_id, source="ledger", content="source row"),
            DebateTranscript(
                investigation_id=imported_id,
                round=1,
                speaker="challenger",
                message="challenge",
                token_count=1,
            ),
            VerificationClaim(investigation_id=imported_id, claim_text="claim", is_grounded=True),
            InvestigationState(
                investigation_id=imported_id,
                phase="test",
                state_json={"ok": True},
                checkpoint_hash="abc",
            ),
            ReviewQueueItem(investigation_id=imported_id, status="pending"),
            ThirdPartyEvidenceVerification(
                claim_id=imported_id,
                category="generic",
                claimed_amount=1000,
                fetched_amount=None,
                tolerance_percentage=0.3,
                provider_name="test_provider",
                verification_status="NEEDS_MANUAL_REVIEW",
                confidence_score=0.3,
                reason="test",
                raw_provider_response_json={},
            ),
            AuditLog(
                investigation_id=imported_id,
                event_type="case_created",
                actor="test",
                details={},
                hash="hash",
                sequence=1,
            ),
        ]
    )
    db.commit()

    r = client.delete("/api/v1/investigations/imported")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted_count"] == 1
    assert imported_id in body["investigation_ids"]

    db.expire_all()
    assert db.get(Investigation, imported_id) is None
    assert db.get(Investigation, manual_id) is not None
    for model in (
        EvidenceArtifact,
        DebateTranscript,
        VerificationClaim,
        InvestigationState,
        ReviewQueueItem,
        AuditLog,
    ):
        assert db.query(model).filter(model.investigation_id == imported_id).count() == 0
    assert db.query(ThirdPartyEvidenceVerification).filter_by(claim_id=imported_id).count() == 0


def test_debate_response_marks_adjudicator_confidence(client, db):
    inv_id = _create(client, txn="TXN-DEBATE")
    investigation = db.get(Investigation, inv_id)
    investigation.confidence = 0.84
    db.add_all(
        [
            DebateTranscript(
                investigation_id=inv_id,
                round=1,
                speaker="challenger",
                message="Amount exceeds materiality without corroboration.",
                token_count=5,
            ),
            DebateTranscript(
                investigation_id=inv_id,
                round=2,
                speaker="adjudicator",
                message="Verdict: high risk at 84% confidence.",
                token_count=7,
            ),
        ]
    )
    db.commit()

    r = client.get(f"/api/v1/investigations/{inv_id}/debate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body[0]["speaker"] == "challenger"
    assert body[0]["confidence"] is None
    assert body[1]["speaker"] == "adjudicator"
    assert body[1]["confidence"] == 0.84


def test_subresource_404_for_missing_case(client):
    r = client.get("/api/v1/investigations/nope/debate")
    assert r.status_code == 404


def test_execute_runs_inline_without_broker(client):
    """With no Celery broker, execute falls back to in-process execution."""
    inv_id = _create(client, txn="TXN-RUN")
    r = client.post(f"/api/v1/investigations/{inv_id}/execute")
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("queued", "running")


def test_execute_falls_back_when_celery_broker_preflight_fails(client, monkeypatch):
    from app.api.routes import investigations as investigation_routes

    previous = settings.USE_CELERY
    settings.USE_CELERY = True
    monkeypatch.setattr(investigation_routes, "_celery_broker_available", lambda: False)

    async def fake_inline(_investigation_id: str) -> None:
        return None

    monkeypatch.setattr(investigation_routes, "_run_investigation_inline", fake_inline)

    try:
        inv_id = _create(client, txn="TXN-CELERY-FALLBACK")
        r = client.post(f"/api/v1/investigations/{inv_id}/execute")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "running"
        assert r.json()["task_id"] is None
        assert "Celery broker unavailable" in r.json()["message"]
    finally:
        settings.USE_CELERY = previous


def test_review_queue_and_actions(client):
    inv_id = _create(client, txn="TXN-REVIEW")
    # Escalate moves it into the queue (critical / human_review).
    r = client.post(f"/api/v1/reviews/{inv_id}/escalate", json={"actor": "alice"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "human_review"

    q = client.get("/api/v1/reviews/queue")
    assert q.status_code == 200
    assert any(item["investigation_id"] == inv_id for item in q.json())
    queued = next(item for item in q.json() if item["investigation_id"] == inv_id)
    assert queued["queue"] == "partner"
    assert queued["assigned_to"] == "engagement_partner"
    assert queued["priority"] == 1

    r = client.post(
        f"/api/v1/reviews/{inv_id}/request-evidence",
        json={"actor": "bob", "comment": "Attach the signed SOW."},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "collecting_evidence"

    r = client.post(f"/api/v1/reviews/{inv_id}/approve", json={"actor": "bob"})
    assert r.status_code == 200
    assert r.json()["status"] == "closed"


def test_review_action_404(client):
    r = client.post("/api/v1/reviews/missing/approve", json={})
    assert r.status_code == 404


def test_auth_register_and_me(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "password123", "role": "analyst"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["username"] == "analyst1"

    # Duplicate registration is rejected.
    r2 = client.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "password123"},
    )
    assert r2.status_code == 409

    token = client.post(
        "/api/v1/auth/token",
        data={"username": "analyst1", "password": "password123"},
    )
    assert token.status_code == 200, token.text

    previous = settings.AUTH_REQUIRED
    settings.AUTH_REQUIRED = True
    try:
        me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token.json()['access_token']}"},
        )
        assert me.status_code == 200, me.text
        assert me.json()["username"] == "analyst1"
    finally:
        settings.AUTH_REQUIRED = previous
