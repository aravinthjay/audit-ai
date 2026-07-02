"""Health-check routes."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db_session
from app.realtime.websocket_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db_session)):
    try:
        db.execute(text("SELECT 1"))
        active = connection_manager.get_all_investigations()
        return {
            "status": "healthy",
            "database": "connected",
            "active_investigations": len(active),
            "websocket_connections": {
                inv_id: connection_manager.get_connection_count(inv_id) for inv_id in active
            },
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})
