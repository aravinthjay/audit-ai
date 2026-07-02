"""
WebSocket connection manager for real-time investigation updates.
Handles connection pooling, broadcasting, and reconnection logic.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per investigation."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_lock = asyncio.Lock()

    async def connect(self, investigation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.connection_lock:
            self.active_connections.setdefault(investigation_id, set()).add(websocket)
        logger.info(
            f"WebSocket connected for {investigation_id}. "
            f"Total: {len(self.active_connections[investigation_id])}"
        )

    async def disconnect(self, investigation_id: str, websocket: WebSocket) -> None:
        async with self.connection_lock:
            if investigation_id in self.active_connections:
                self.active_connections[investigation_id].discard(websocket)
                if not self.active_connections[investigation_id]:
                    del self.active_connections[investigation_id]
        logger.info(f"WebSocket disconnected for {investigation_id}")

    async def broadcast(
        self,
        investigation_id: str,
        message: Dict[str, Any],
        exclude: Optional[WebSocket] = None,
    ) -> None:
        if investigation_id not in self.active_connections:
            return

        message.setdefault("timestamp", datetime.utcnow().isoformat())
        json_data = json.dumps(message, default=str)
        disconnected = set()

        async with self.connection_lock:
            connections = self.active_connections.get(investigation_id, set()).copy()

        for connection in connections:
            if exclude and connection is exclude:
                continue
            try:
                await connection.send_text(json_data)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to send to connection: {e}")
                disconnected.add(connection)

        for connection in disconnected:
            await self.disconnect(investigation_id, connection)

    async def broadcast_all(self, message: Dict[str, Any]) -> None:
        message.setdefault("timestamp", datetime.utcnow().isoformat())
        for investigation_id in list(self.active_connections.keys()):
            await self.broadcast(investigation_id, message)

    def get_connection_count(self, investigation_id: str) -> int:
        return len(self.active_connections.get(investigation_id, set()))

    def get_all_investigations(self) -> list[str]:
        return list(self.active_connections.keys())


connection_manager = ConnectionManager()


class AgentStatusUpdateEvent:
    """Agent execution status update event."""

    TYPE = "agent_status"

    def __init__(self, investigation_id, agent, state, message="", metadata=None):
        self.investigation_id = investigation_id
        self.agent = agent
        self.state = state
        self.message = message
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.TYPE,
            "investigation_id": self.investigation_id,
            "agent": self.agent,
            "state": self.state,
            "message": self.message,
            "metadata": self.metadata,
        }


class DebateMessageEvent:
    """Debate round message event."""

    TYPE = "debate_message"

    def __init__(self, investigation_id, round, speaker, message, metadata=None):
        self.investigation_id = investigation_id
        self.round = round
        self.speaker = speaker
        self.message = message
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.TYPE,
            "investigation_id": self.investigation_id,
            "round": self.round,
            "speaker": self.speaker,
            "message": self.message,
            "metadata": self.metadata,
        }


class PipelineStageEvent:
    """Investigation pipeline stage transition event."""

    TYPE = "pipeline_stage"

    def __init__(self, investigation_id, from_stage, to_stage, metadata=None):
        self.investigation_id = investigation_id
        self.from_stage = from_stage
        self.to_stage = to_stage
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.TYPE,
            "investigation_id": self.investigation_id,
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "metadata": self.metadata,
        }


class ReviewQueueEvent:
    """Review queue action event."""

    TYPE = "review_queue"

    def __init__(self, investigation_id, action, actor, metadata=None):
        self.investigation_id = investigation_id
        self.action = action
        self.actor = actor
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.TYPE,
            "investigation_id": self.investigation_id,
            "action": self.action,
            "actor": self.actor,
            "metadata": self.metadata,
        }


class VerificationEvent:
    """Claim verification event."""

    TYPE = "verification"

    def __init__(self, investigation_id, claim_id, status, metadata=None):
        self.investigation_id = investigation_id
        self.claim_id = claim_id
        self.status = status
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.TYPE,
            "investigation_id": self.investigation_id,
            "claim_id": self.claim_id,
            "status": self.status,
            "metadata": self.metadata,
        }
