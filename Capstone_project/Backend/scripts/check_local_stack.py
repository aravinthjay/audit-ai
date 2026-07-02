r"""Preflight checks for the local production-like backend stack.

Run from Backend:
    .\.venv\Scripts\python.exe scripts\check_local_stack.py
"""

from __future__ import annotations

import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.session import engine


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _redis_check() -> Check:
    if not (settings.USE_CELERY or settings.USE_REDIS_EVENTS):
        return Check("Redis", True, "not required by current settings")

    try:
        import redis

        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        client.ping()
        client.close()
        return Check("Redis", True, settings.REDIS_URL)
    except Exception as exc:  # noqa: BLE001
        return Check("Redis", False, f"{settings.REDIS_URL} failed: {exc}")


def _celery_broker_check() -> Check:
    if not settings.USE_CELERY:
        return Check("Celery broker", True, "not required by current settings")

    try:
        from app.tasks.celery_app import app as celery_app

        with celery_app.connection_for_write() as connection:
            connection.ensure_connection(max_retries=1)
        return Check("Celery broker", True, settings.CELERY_BROKER_URL)
    except Exception as exc:  # noqa: BLE001
        return Check("Celery broker", False, f"{settings.CELERY_BROKER_URL} failed: {exc}")


def _database_check() -> Check:
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        return Check("PostgreSQL", True, settings.DATABASE_URL)
    except Exception as exc:  # noqa: BLE001
        return Check("PostgreSQL", False, f"{settings.DATABASE_URL} failed: {exc}")


def _eventstore_check() -> Check:
    if not settings.USE_EVENTSTORE:
        return Check("EventStoreDB", True, "not required by current settings")

    parsed = urlparse(settings.EVENTSTORE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 2113
    health_url = f"http://{host}:{port}/health/live"

    if not _port_open(host, port):
        return Check("EventStoreDB", False, f"{settings.EVENTSTORE_URL} is not reachable")

    try:
        with urllib.request.urlopen(health_url, timeout=2) as response:  # noqa: S310
            if 200 <= response.status < 300:
                return Check("EventStoreDB", True, health_url)
            return Check("EventStoreDB", False, f"{health_url} returned {response.status}")
    except urllib.error.URLError as exc:
        return Check("EventStoreDB", False, f"{health_url} failed: {exc}")


def _llm_provider_check() -> Check:
    if not settings.USE_REAL_AGENTS:
        return Check("LLM provider", True, "not required while USE_REAL_AGENTS=false")

    key_env = {
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
    }[settings.DEFAULT_LLM_PROVIDER]
    key_value = str(getattr(settings, key_env, "") or "")
    if not key_value or "replace-with" in key_value:
        return Check("LLM provider", False, f"{key_env} is missing or still a placeholder")

    if settings.ENABLE_LLM_FALLBACK:
        configured_fallbacks = []
        for provider in settings.LLM_FALLBACK_ORDER:
            normalized = provider.strip().lower()
            fallback_env = {
                "anthropic": "ANTHROPIC_API_KEY",
                "groq": "GROQ_API_KEY",
                "openai": "OPENAI_API_KEY",
            }.get(normalized)
            if fallback_env and str(getattr(settings, fallback_env, "") or "").strip():
                configured_fallbacks.append(normalized)
        if not configured_fallbacks:
            return Check("LLM provider", False, "fallback is enabled but no fallback provider key is configured")
        fallback_detail = f"; fallback ready: {', '.join(configured_fallbacks)}"
    else:
        fallback_detail = "; fallback disabled"

    return Check("LLM provider", True, f"default={settings.DEFAULT_LLM_PROVIDER} via {key_env}{fallback_detail}")


def main() -> int:
    checks = [
        _database_check(),
        _redis_check(),
        _celery_broker_check(),
        _eventstore_check(),
        _llm_provider_check(),
    ]

    width = max(len(check.name) for check in checks)
    for check in checks:
        status = "OK" if check.ok else "FAIL"
        print(f"{status:4} {check.name:<{width}} {check.detail}")

    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
