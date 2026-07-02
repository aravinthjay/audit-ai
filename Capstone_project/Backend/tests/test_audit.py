"""Audit hash-chain tests (Postgres/SQLite fallback path)."""

import asyncio

from app.audit.eventstore import AuditEvent, EventStoreAuditLog


class _AsyncEventIterator:
    def __init__(self, events):
        self._events = iter(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._events)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _RecordedEvent:
    id = "event-1"
    type = "case_created"
    data = b'{"event_type":"case_created","investigation_id":"case-1"}'


class _CoroutineReadClient:
    async def read_stream(self, stream_name):
        assert stream_name.endswith("case-1")
        return _AsyncEventIterator([_RecordedEvent()])


class _FailingReadClient:
    def __init__(self):
        self.calls = 0

    async def read_stream(self, stream_name):
        self.calls += 1
        raise ConnectionError("EventStore unavailable")


def test_audit_chain_is_tamper_evident(db):
    log = EventStoreAuditLog("esdb://unreachable:2113?tls=false")
    asyncio.run(log.connect())
    assert log._esdb_available is False

    inv_id = "audit-test-1"
    for i in range(3):
        log._append_postgres(AuditEvent("step", inv_id, "system", {"i": i}))

    assert asyncio.run(log.verify_chain_integrity(inv_id)) is True

    from app.db.models import AuditLog

    row = (
        db.query(AuditLog)
        .filter_by(investigation_id=inv_id)
        .order_by(AuditLog.sequence.asc())
        .first()
    )
    row.details = {"i": 999}
    db.commit()

    assert asyncio.run(log.verify_chain_integrity(inv_id)) is False


def test_eventstore_read_stream_coroutine_client_is_supported():
    log = EventStoreAuditLog("esdb://eventstore:2113?tls=false")
    log.client = _CoroutineReadClient()
    log._esdb_available = True

    events = asyncio.run(log.get_events("case-1"))

    assert events == [
        {
            "id": "event-1",
            "type": "case_created",
            "data": {"event_type": "case_created", "investigation_id": "case-1"},
        }
    ]


def test_eventstore_read_failure_disables_retries(db):
    client = _FailingReadClient()
    log = EventStoreAuditLog("esdb://eventstore:2113?tls=false")
    log.client = client
    log._esdb_available = True

    inv_id = "audit-fallback-1"
    log._append_postgres(AuditEvent("case_created", inv_id, "system", {"source": "test"}))

    first = asyncio.run(log.get_events(inv_id))
    second = asyncio.run(log.get_events(inv_id))

    assert client.calls == 1
    assert log._esdb_available is False
    assert first[0]["type"] == "case_created"
    assert second[0]["type"] == "case_created"
