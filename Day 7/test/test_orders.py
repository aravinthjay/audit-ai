"""
tests/test_orders.py — Pytest suite
=====================================
Run: pytest tests/ -v
"""

import sys, os
#sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


client = TestClient(app)

# ── Fixtures ────────────────────────────────────────────────────────────────

ORDER_PAYLOAD = {
    "customer": {
        "name": "Aarav Sharma",
        "email": "aarav@example.com",
        "phone": "+919876543210",
        "shipping_address": {
            "street": "42 MG Road",
            "city": "Dehradun",
            "state": "Uttarakhand",
            "pincode": "248001",
            "country": "India",
        },
    },
    "items": [
        {
            "product": {
                "name": "Wireless Headphones",
                "price": 2999.00,
                "sku": "WH-001",
            },
            "quantity": 2,
            "discount": 10.0,
        },
        {
            "product": {
                "name": "USB-C Cable",
                "price": 499.00,
                "sku": "UC-002",
            },
            "quantity": 3,
            "discount": 0.0,
        },
    ],
    "payment_method": "upi",
    "notes": "Leave at gate",
}


# ── Tests ────────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_order_returns_summary():
    r = client.post("/orders/", json=ORDER_PAYLOAD)
    assert r.status_code == 201
    data = r.json()

    # Extension model check
    assert "summary" in data
    summary = data["summary"]
    assert summary["item_count"] == 5  # 2+3
    # subtotal = 2*2999 + 3*499 = 5998 + 1497 = 7495
    assert summary["subtotal"] == 7495.0
    # discount on item1 = 10% of 5998 = 599.8
    assert summary["total_discount"] == pytest.approx(599.8, rel=1e-3)
    assert summary["grand_total"] == pytest.approx(6895.2, rel=1e-3)


def test_create_order_nested_fields():
    r = client.post("/orders/", json=ORDER_PAYLOAD)
    assert r.status_code == 201
    data = r.json()

    # Nested customer → address
    assert data["customer"]["shipping_address"]["pincode"] == "248001"
    # billing_address defaults to shipping
    assert data["customer"]["billing_address"]["city"] == "Dehradun"

    # Nested item → product
    assert data["items"][0]["product"]["name"] == "Wireless Headphones"


def test_list_orders():
    client.post("/orders/", json=ORDER_PAYLOAD)
    r = client.get("/orders/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_get_order_by_id():
    create_r = client.post("/orders/", json=ORDER_PAYLOAD)
    order_id = create_r.json()["id"]

    r = client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    assert r.json()["id"] == order_id


def test_get_order_not_found():
    r = client.get(f"/orders/{uuid4()}")
    assert r.status_code == 404


def test_update_order_status():
    create_r = client.post("/orders/", json=ORDER_PAYLOAD)
    order_id = create_r.json()["id"]

    r = client.patch(f"/orders/{order_id}/status?new_status=confirmed")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"


def test_delete_order():
    create_r = client.post("/orders/", json=ORDER_PAYLOAD)
    order_id = create_r.json()["id"]

    del_r = client.delete(f"/orders/{order_id}")
    assert del_r.status_code == 204

    get_r = client.get(f"/orders/{order_id}")
    assert get_r.status_code == 404


def test_invalid_pincode():
    bad_payload = {**ORDER_PAYLOAD}
    bad_payload["customer"] = {
        **ORDER_PAYLOAD["customer"],
        "shipping_address": {**ORDER_PAYLOAD["customer"]["shipping_address"], "pincode": "12AB"},
    }
    r = client.post("/orders/", json=bad_payload)
    assert r.status_code == 422


def test_empty_items_rejected():
    bad_payload = {**ORDER_PAYLOAD, "items": []}
    r = client.post("/orders/", json=bad_payload)
    assert r.status_code == 422

import asyncio
import nest_asyncio
import uvicorn

nest_asyncio.apply()

config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
server = uvicorn.Server(config)

# Run the server as an asyncio task to avoid event loop conflicts in Colab
asyncio.create_task(server.serve())

# pip install ipytest -q

import ipytest
ipytest.autoconfig()
