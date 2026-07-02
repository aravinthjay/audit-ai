"""Tests for real-time third-party evidence verification."""

import requests

from app.core.config import settings
from app.db.models import ThirdPartyEvidenceVerification


class _ProviderResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _patch_provider(monkeypatch, setting_name, payload):
    previous = getattr(settings, setting_name)
    setattr(settings, setting_name, f"https://third-party.example/{setting_name.lower()}")

    def fake_post(url, json, headers, timeout):
        assert url == getattr(settings, setting_name)
        assert headers["Accept"] == "application/json"
        assert timeout == settings.EVIDENCE_VERIFICATION_PROVIDER_TIMEOUT_SECONDS
        assert json["claimed_amount"] > 0
        return _ProviderResponse(payload)

    monkeypatch.setattr("app.evidence_verification.service.requests.post", fake_post)
    return previous


def test_missing_provider_url_returns_api_unavailable(client):
    response = client.post(
        "/api/v1/claims/verify-preview",
        json={
            "category": "fuel",
            "claimed_amount": 1050,
            "quantity": 10,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verification_status"] == "API_UNAVAILABLE"
    assert body["fetched_amount"] is None
    assert "No real-time third-party provider URL is configured" in body["reason"]


def test_claim_creation_auto_runs_configured_flight_provider(client, db, monkeypatch):
    previous = _patch_provider(
        monkeypatch,
        "FLIGHT_PRICE_PROVIDER_URL",
        {
            "provider_name": "live_flight_fare_api",
            "reference_amount": 7500,
            "provider_reference_id": "LIVE-FLIGHT-123",
            "confidence": 0.81,
            "reason": (
                "Real-time comparable fare for Puducherry to Bengaluru. "
                "Provider used Chennai (MAA) as nearest comparable airport."
            ),
        },
    )

    try:
        response = client.post(
            "/api/v1/investigations",
            json={
                "transaction_id": "TRX-FLIGHT-1",
                "vendor": "Swift Travel",
                "category": "flight ticket",
                "amount": 20000,
                "description": "Puducherry to Bengaluru flight on 2026-07-10.",
            },
        )
    finally:
        settings.FLIGHT_PRICE_PROVIDER_URL = previous

    assert response.status_code == 201, response.text
    claim_id = response.json()["id"]

    verification_response = client.get(f"/api/v1/claims/{claim_id}/verification")
    assert verification_response.status_code == 200, verification_response.text
    body = verification_response.json()
    assert body["verification_status"] == "FLAGGED"
    assert body["claimed_amount"] == 20000
    assert body["fetched_amount"] == 7500
    assert body["provider_name"] == "live_flight_fare_api"
    assert body["provider_reference_id"] == "LIVE-FLIGHT-123"
    assert body["tolerance_percentage"] == 0.25
    assert "Chennai (MAA)" in body["reason"]

    row = db.query(ThirdPartyEvidenceVerification).filter_by(claim_id=claim_id).first()
    assert row is not None
    assert row.raw_provider_response_json["provider_reference_id"] == "LIVE-FLIGHT-123"


def test_configured_fuel_provider_within_tolerance_is_verified(client, monkeypatch):
    previous = _patch_provider(
        monkeypatch,
        "FUEL_PRICE_PROVIDER_URL",
        {
            "provider_name": "live_fuel_price_api",
            "reference_amount": 1020,
            "provider_reference_id": "FUEL-20260630-BLR",
            "confidence": 0.9,
            "reason": "Daily fuel price API returned location-specific pump price.",
        },
    )

    try:
        response = client.post(
            "/api/v1/claims/verify-preview",
            json={"category": "fuel", "claimed_amount": 1050, "quantity": 10},
        )
    finally:
        settings.FUEL_PRICE_PROVIDER_URL = previous

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verification_status"] == "VERIFIED"
    assert body["fetched_amount"] == 1020
    assert body["provider_name"] == "live_fuel_price_api"
    assert body["tolerance_percentage"] == 0.1


def test_configured_fuel_provider_above_tolerance_is_flagged(client, monkeypatch):
    previous = _patch_provider(
        monkeypatch,
        "FUEL_PRICE_PROVIDER_URL",
        {
            "provider_name": "live_fuel_price_api",
            "reference_amount": 1020,
            "provider_reference_id": "FUEL-20260630-BLR",
            "confidence": 0.9,
            "reason": "Daily fuel price API returned location-specific pump price.",
        },
    )

    try:
        response = client.post(
            "/api/v1/claims/verify-preview",
            json={"category": "fuel", "claimed_amount": 2000, "quantity": 10},
        )
    finally:
        settings.FUEL_PRICE_PROVIDER_URL = previous

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verification_status"] == "FLAGGED"
    assert body["difference_percentage"] > 0.1


def test_provider_timeout_returns_api_unavailable(client, monkeypatch):
    previous = settings.CAB_FARE_PROVIDER_URL
    settings.CAB_FARE_PROVIDER_URL = "https://third-party.example/cab"

    def fake_post(url, json, headers, timeout):
        del url, json, headers, timeout
        raise requests.Timeout("cab provider timed out")

    monkeypatch.setattr("app.evidence_verification.service.requests.post", fake_post)

    try:
        response = client.post(
            "/api/v1/claims/verify-preview",
            json={
                "category": "cab",
                "claimed_amount": 500,
                "route_from": "Indiranagar",
                "route_to": "MG Road",
            },
        )
    finally:
        settings.CAB_FARE_PROVIDER_URL = previous

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verification_status"] == "API_UNAVAILABLE"
    assert "timed out" in body["reason"]


def test_gstin_invalid_format_is_flagged_without_provider_call(client, monkeypatch):
    called = False

    def fake_post(url, json, headers, timeout):
        nonlocal called
        called = True
        return _ProviderResponse({})

    monkeypatch.setattr("app.evidence_verification.service.requests.post", fake_post)
    response = client.post(
        "/api/v1/claims/verify-preview",
        json={
            "category": "GST invoice",
            "claimed_amount": 1180,
            "gstin": "BADGSTIN",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verification_status"] == "FLAGGED"
    assert body["provider_name"] == "local_gstin_validation"
    assert "GSTIN format is invalid" in body["reason"]
    assert called is False


def test_food_without_realtime_provider_is_api_unavailable(client):
    response = client.post(
        "/api/v1/claims/verify-preview",
        json={
            "category": "food",
            "claimed_amount": 1500,
            "vendor": "Cafe Example",
            "location": "Bengaluru",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verification_status"] == "API_UNAVAILABLE"
    assert body["fetched_amount"] is None
