"""
Redis pub/sub event bus.

Bridges the Celery worker process and the FastAPI process: the worker publishes
JSON events to a per-investigation Redis channel, and the API process subscribes
and forwards them to connected WebSocket clients.
"""

import json
import logging
from typing import Any, AsyncIterator, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


def _channel(investigation_id: str) -> str:
    return f"{settings.REDIS_EVENT_CHANNEL_PREFIX}:{investigation_id}"


def publish_event(investigation_id: str, message: Dict[str, Any]) -> None:
    """Publish an event to an investigation's channel (sync, for the worker)."""
    if not settings.USE_REDIS_EVENTS:
        return

    try:
        import redis

        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        client.publish(_channel(investigation_id), json.dumps(message, default=str))
        client.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to publish event to Redis: {exc}")


async def subscribe_events(investigation_id: str) -> AsyncIterator[Dict[str, Any]]:
    """Yield events for an investigation as they arrive (async, for the API)."""
    if not settings.USE_REDIS_EVENTS:
        return

    import redis.asyncio as aioredis

    client = aioredis.Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    )
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(investigation_id))
    try:
        async for raw in pubsub.listen():
            if raw is None or raw.get("type") != "message":
                continue
            data = raw.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                yield json.loads(data)
            except (json.JSONDecodeError, TypeError):
                logger.debug("Dropping non-JSON pubsub payload")
    finally:
        try:
            await pubsub.unsubscribe(_channel(investigation_id))
            await pubsub.aclose()
            await client.aclose()
        except Exception:  # noqa: BLE001
            pass
