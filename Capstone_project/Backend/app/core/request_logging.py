"""Request logging middleware for production telemetry."""

import logging
import time
import uuid

from fastapi import Request
from starlette.types import ASGIApp

from app.core.config import settings
from app.db.models import RequestLog
from app.db.session import SessionLocal

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware:
    """Persist request telemetry and attach a stable request id response header."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.excluded_paths = set(settings.REQUEST_LOG_EXCLUDED_PATHS)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            path = request.url.path
            if settings.REQUEST_LOGGING_ENABLED and path not in self.excluded_paths:
                self._record(request, request_id, status_code, duration_ms)

    def _record(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        user_id = getattr(getattr(request.state, "user", None), "username", None)
        db = SessionLocal()
        try:
            db.add(
                RequestLog(
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    client_host=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    user_id=user_id,
                )
            )
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.warning("Request telemetry write failed: %s", exc)
        finally:
            db.close()

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )


def add_request_logging_middleware(app) -> None:
    app.add_middleware(RequestLoggingMiddleware)
