"""API endpoint tests."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_detailed_health(client):
    r = client.get("/health/detailed")
    assert r.status_code == 200
    assert r.json()["database"] == "connected"


def test_create_investigation_validates_body(client):
    r = client.post("/api/v1/investigations", json={"vendor": "Acme"})
    assert r.status_code == 422


def test_create_and_fetch_investigation(client):
    payload = {
        "transaction_id": "TXN-001",
        "vendor": "Acme Corp",
        "category": "consulting",
        "amount": 75000.0,
    }
    r = client.post("/api/v1/investigations", json=payload)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["transaction_id"] == "TXN-001"
    assert created["status"] == "intake"

    inv_id = created["id"]
    r2 = client.get(f"/api/v1/investigations/{inv_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == inv_id


def test_list_investigations(client):
    client.post(
        "/api/v1/investigations",
        json={"transaction_id": "TXN-LIST", "vendor": "Beta", "category": "travel", "amount": 1000.0},
    )
    r = client.get("/api/v1/investigations?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert isinstance(body["investigations"], list)


def test_get_missing_investigation_returns_404(client):
    r = client.get("/api/v1/investigations/does-not-exist")
    assert r.status_code == 404


def test_register_rejects_duplicate_email(client):
    payload = {
        "username": "email-user-a",
        "password": "super-secret-pw",
        "email": "duplicate@example.test",
        "role": "analyst",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        "/api/v1/auth/register",
        json={**payload, "username": "email-user-b"},
    )

    assert r2.status_code == 409
    assert r2.json()["detail"] == "Email already exists"


def test_register_rejects_unknown_role(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": "role-user",
            "password": "super-secret-pw",
            "email": "role-user@example.test",
            "role": "owner",
        },
    )

    assert r.status_code == 422
