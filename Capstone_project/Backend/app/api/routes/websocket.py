"""Real-time WebSocket route."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.websocket_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/investigations/{investigation_id}")
async def websocket_investigation_endpoint(websocket: WebSocket, investigation_id: str):
    """Stream real-time investigation updates to a client."""
    await connection_manager.connect(investigation_id, websocket)
    logger.info(f"WebSocket connected for investigation {investigation_id}")

    forward_task = asyncio.create_task(_forward_redis_events(investigation_id, websocket))
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WS message on {investigation_id}: {data}")
            await websocket.send_json({"type": "ack", "investigation_id": investigation_id})
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for investigation {investigation_id}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"WebSocket error for {investigation_id}: {e}", exc_info=True)
    finally:
        forward_task.cancel()
        await connection_manager.disconnect(investigation_id, websocket)


async def _forward_redis_events(investigation_id: str, websocket: WebSocket) -> None:
    try:
        from app.realtime.redis_bus import subscribe_events

        async for event in subscribe_events(investigation_id):
            await websocket.send_json(event)
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Redis forwarding stopped for {investigation_id}: {e}")
