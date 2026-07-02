"""
Immutable audit trail.

Primary store: EventStoreDB (append-only event streams), via the maintained
`esdbclient` package (lazy-imported so the app boots without it).

Fallback store: a SHA256 hash-chained `audit_log` table in PostgreSQL. The
fallback is a real tamper-evident chain (each row's hash covers the previous
hash), unlike the previous placeholder implementation.
"""

import hashlib
import inspect
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _canonical(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


def _hash(prev_hash: Optional[str], payload: Dict[str, Any]) -> str:
    return hashlib.sha256(f"{prev_hash or ''}|{_canonical(payload)}".encode()).hexdigest()


class AuditEvent:
    """Represents an audit event."""

    def __init__(self, event_type, investigation_id, actor, details, timestamp=None):
        self.event_type = event_type
        self.investigation_id = investigation_id
        self.actor = actor
        self.details = details
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "investigation_id": self.investigation_id,
            "actor": self.actor,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class EventStoreAuditLog:
    """Append-only audit log with EventStoreDB primary + Postgres fallback."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.client = None
        self.stream_prefix = settings.EVENTSTORE_STREAM_PREFIX
        self._esdb_available = False

    def _disable_eventstore(self, operation: str, error: Exception) -> None:
        self.client = None
        self._esdb_available = False
        if settings.AUDIT_FALLBACK_TO_POSTGRES:
            logger.warning(
                "EventStore %s failed; using Postgres audit fallback until restart: %s",
                operation,
                error,
            )
            return

        raise error

    async def connect(self) -> None:
        if not settings.USE_EVENTSTORE:
            self.client = None
            self._esdb_available = False
            logger.info("EventStoreDB disabled; using Postgres audit fallback")
            return

        try:
            from esdbclient import AsyncEventStoreDBClient

            client = AsyncEventStoreDBClient(uri=self.connection_string)
            connect = getattr(client, "connect", None)
            if connect is not None:
                await connect()
            self.client = client
            self._esdb_available = True
            logger.info("Connected to EventStoreDB")
        except Exception as e:  # noqa: BLE001
            self.client = None
            self._esdb_available = False
            if settings.AUDIT_FALLBACK_TO_POSTGRES:
                logger.warning("EventStoreDB unavailable (%s); using Postgres fallback", e)
            else:
                raise

    async def disconnect(self) -> None:
        if self.client is not None:
            close = getattr(self.client, "close", None)
            if close is not None:
                try:
                    await close()
                except Exception:  # noqa: BLE001
                    pass

    def _get_stream_name(self, investigation_id: str) -> str:
        return f"{self.stream_prefix}-{investigation_id}"

    async def append_event(self, event: AuditEvent) -> str:
        if self._esdb_available and self.client is not None:
            try:
                from esdbclient import NewEvent, StreamState

                new_event = NewEvent(
                    type=event.event_type,
                    data=_canonical(event.to_dict()).encode("utf-8"),
                    metadata=_canonical(
                        {"actor": event.actor, "investigation_id": event.investigation_id}
                    ).encode("utf-8"),
                )
                commit = await self.client.append_to_stream(
                    self._get_stream_name(event.investigation_id),
                    events=[new_event],
                    current_version=StreamState.ANY,
                )
                return str(commit)
            except Exception as e:  # noqa: BLE001
                self._disable_eventstore("append", e)

        return self._append_postgres(event)

    def _append_postgres(self, event: AuditEvent) -> str:
        from app.db.models import AuditLog
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            last = (
                db.query(AuditLog)
                .filter(AuditLog.investigation_id == event.investigation_id)
                .order_by(AuditLog.sequence.desc())
                .first()
            )
            prev_hash = last.hash if last else None
            sequence = (last.sequence + 1) if last else 0

            payload = event.to_dict()
            row_hash = _hash(prev_hash, payload)

            row = AuditLog(
                investigation_id=event.investigation_id,
                event_type=event.event_type,
                actor=event.actor,
                details=payload,
                hash=row_hash,
                prev_hash=prev_hash,
                sequence=sequence,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()

    async def get_events(self, investigation_id, start_position=0, limit=None):
        del start_position
        if self._esdb_available and self.client is not None:
            try:
                events: List[Dict[str, Any]] = []
                read = getattr(self.client, "read_stream", None) or getattr(self.client, "read")
                stream = read(self._get_stream_name(investigation_id))
                if inspect.isawaitable(stream):
                    stream = await stream

                async for event in stream:
                    data = getattr(event, "data", b"{}") or b"{}"
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    events.append(
                        {
                            "id": str(getattr(event, "id", "")),
                            "type": getattr(event, "type", ""),
                            "data": json.loads(data) if isinstance(data, str) else data,
                        }
                    )
                    if limit and len(events) >= limit:
                        break
                return events
            except Exception as e:  # noqa: BLE001
                self._disable_eventstore("read", e)

        return self._get_events_postgres(investigation_id, limit)

    def _get_events_postgres(self, investigation_id, limit):
        from app.db.models import AuditLog
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            q = (
                db.query(AuditLog)
                .filter(AuditLog.investigation_id == investigation_id)
                .order_by(AuditLog.sequence.asc())
            )
            if limit:
                q = q.limit(limit)
            return [
                {
                    "id": r.id,
                    "type": r.event_type,
                    "data": r.details,
                    "hash": r.hash,
                    "prev_hash": r.prev_hash,
                    "sequence": r.sequence,
                }
                for r in q.all()
            ]
        finally:
            db.close()

    async def get_all_events(self, investigation_id):
        return await self.get_events(investigation_id)

    async def verify_chain_integrity(self, investigation_id) -> bool:
        events = self._get_events_postgres(investigation_id, None)
        if not events:
            return True

        prev_hash = None
        for ev in events:
            expected = _hash(prev_hash, ev["data"])
            if ev.get("hash") != expected:
                logger.error(
                    "Audit chain broken at sequence %s for %s",
                    ev.get("sequence"),
                    investigation_id,
                )
                return False
            prev_hash = ev["hash"]
        return True


class AuditEventType:
    """Audit event type constants."""

    CASE_CREATED = "case_created"
    EVIDENCE_COLLECTED = "evidence_collected"
    DEBATE_STARTED = "debate_started"
    DEBATE_ROUND_COMPLETED = "debate_round_completed"
    ADJUDICATION_COMPLETED = "adjudication_completed"
    VERIFICATION_COMPLETED = "verification_completed"
    CASE_APPROVED = "case_approved"
    CASE_REJECTED = "case_rejected"
    CASE_ESCALATED = "case_escalated"
    CASE_CLOSED = "case_closed"
    HUMAN_REVIEW_STARTED = "human_review_started"
    HUMAN_REVIEW_COMPLETED = "human_review_completed"


audit_log: Optional[EventStoreAuditLog] = None


async def get_audit_log() -> EventStoreAuditLog:
    global audit_log
    if audit_log is None:
        audit_log = EventStoreAuditLog(settings.EVENTSTORE_URL)
        await audit_log.connect()
    return audit_log


async def _log(event_type, investigation_id, actor, details) -> None:
    instance = await get_audit_log()
    await instance.append_event(
        AuditEvent(event_type=event_type, investigation_id=investigation_id, actor=actor, details=details)
    )


async def log_case_created(investigation_id, actor, details) -> None:
    await _log(AuditEventType.CASE_CREATED, investigation_id, actor, details)


async def log_evidence_collected(investigation_id, actor, details) -> None:
    await _log(AuditEventType.EVIDENCE_COLLECTED, investigation_id, actor, details)


async def log_debate_started(investigation_id, actor, details) -> None:
    await _log(AuditEventType.DEBATE_STARTED, investigation_id, actor, details)


async def log_debate_round_completed(investigation_id, actor, details) -> None:
    await _log(AuditEventType.DEBATE_ROUND_COMPLETED, investigation_id, actor, details)


async def log_adjudication_completed(investigation_id, actor, details) -> None:
    await _log(AuditEventType.ADJUDICATION_COMPLETED, investigation_id, actor, details)


async def log_verification_completed(investigation_id, actor, details) -> None:
    await _log(AuditEventType.VERIFICATION_COMPLETED, investigation_id, actor, details)


async def log_case_approved(investigation_id, actor, details) -> None:
    await _log(AuditEventType.CASE_APPROVED, investigation_id, actor, details)


async def log_case_rejected(investigation_id, actor, details) -> None:
    await _log(AuditEventType.CASE_REJECTED, investigation_id, actor, details)


async def log_case_escalated(investigation_id, actor, details) -> None:
    await _log(AuditEventType.CASE_ESCALATED, investigation_id, actor, details)


async def log_case_closed(investigation_id, actor, details) -> None:
    await _log(AuditEventType.CASE_CLOSED, investigation_id, actor, details)
