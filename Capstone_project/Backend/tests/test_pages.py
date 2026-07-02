"""Endpoint tests for the pages that previously had no backing API:
analytics, reports, knowledge base, global audit, and replay."""

from app.db.models import Investigation, InvestigationStatus, VerificationClaim


def test_knowledge_sources(client):
    r = client.get("/api/v1/knowledge/sources")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) >= 5
    for source in body:
        assert {"id", "title", "clause_preview", "embedding_status", "version_history"} <= set(source)


def test_knowledge_chunks_and_search(client):
    reindex = client.post("/api/v1/knowledge/reindex")
    assert reindex.status_code == 200, reindex.text
    assert reindex.json()["synced_chunks"] >= 10

    chunks = client.get("/api/v1/knowledge/chunks")
    assert chunks.status_code == 200, chunks.text
    body = chunks.json()
    assert len(body) >= 10
    assert {"id", "source_id", "content", "keywords"} <= set(body[0])

    search = client.get("/api/v1/knowledge/search?q=flight%20benchmark&limit=3")
    assert search.status_code == 200, search.text
    results = search.json()
    assert results
    assert any("flight" in item["content"].lower() for item in results)
    assert {"score", "lexical_score", "vector_score"} <= set(results[0])


def test_analytics_endpoints_return_lists(client):
    for path in ("trend", "agent-accuracy", "kpis"):
        r = client.get(f"/api/v1/analytics/{path}")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)


def test_global_audit_recent(client):
    r = client.get("/api/v1/audit/recent")
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


def test_reports_lists_reportable_cases(client, db):
    inv = Investigation(
        transaction_id="RPT-1",
        vendor="Acme",
        category="consulting",
        amount=60000.0,
        confidence=0.9,
        status=InvestigationStatus.REPORT_READY,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    r = client.get("/api/v1/reports")
    assert r.status_code == 200, r.text
    reports = r.json()
    record = next((x for x in reports if x["investigation_id"] == inv.id), None)
    assert record is not None
    assert record["status"] in ("ready", "approved", "draft")
    assert {"executive_summary", "risk_verdict", "sections", "audience"} <= set(record)


def test_intake_only_case_not_in_reports(client, db):
    inv = Investigation(
        transaction_id="RPT-INTAKE",
        vendor="Beta",
        category="travel",
        amount=100.0,
        status=InvestigationStatus.INTAKE,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    r = client.get("/api/v1/reports")
    assert r.status_code == 200
    assert all(x["investigation_id"] != inv.id for x in r.json())


def test_analytics_kpis_with_data(client, db):
    inv = Investigation(
        transaction_id="AN-1",
        vendor="Gamma",
        category="ops",
        amount=5000.0,
        confidence=0.85,
        status=InvestigationStatus.CLOSED,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    db.add(VerificationClaim(investigation_id=inv.id, claim_text="c", is_grounded=True))
    db.commit()

    r = client.get("/api/v1/analytics/kpis")
    assert r.status_code == 200
    labels = {k["label"] for k in r.json()}
    assert "Grounding rate" in labels and "Avg confidence" in labels


def test_replay_for_investigation(client, db):
    inv = Investigation(
        transaction_id="RPL-1",
        vendor="Delta",
        category="ops",
        amount=1000.0,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    r = client.get(f"/api/v1/investigations/{inv.id}/replay")
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


def test_replay_missing_investigation_404(client):
    r = client.get("/api/v1/investigations/does-not-exist/replay")
    assert r.status_code == 404


def test_list_has_debate_filter(client, db):
    from app.db.models import DebateTranscript

    # Case with a debate transcript.
    with_debate = Investigation(
        transaction_id="DBT-1", vendor="Meta", category="ads", amount=3181.0
    )
    # Case without any debate.
    without_debate = Investigation(
        transaction_id="DBT-2", vendor="Nilo", category="ops", amount=500.0
    )
    db.add_all([with_debate, without_debate])
    db.commit()
    db.refresh(with_debate)
    db.refresh(without_debate)
    db.add(
        DebateTranscript(
            investigation_id=with_debate.id,
            round=1,
            speaker="challenger",
            message="Exceeds materiality.",
            token_count=3,
        )
    )
    db.commit()

    r = client.get("/api/v1/investigations?has_debate=true&limit=500")
    assert r.status_code == 200, r.text
    ids = {item["id"] for item in r.json()["investigations"]}
    assert with_debate.id in ids
    assert without_debate.id not in ids
