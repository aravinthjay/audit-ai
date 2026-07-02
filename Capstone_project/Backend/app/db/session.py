"""
Database session management.
Handles connection pooling, session lifecycle, and transaction management.
"""

import logging
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.db.models import Base

logger = logging.getLogger(__name__)

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_is_postgres = "postgresql" in settings.DATABASE_URL


def _build_engine_kwargs() -> dict:
    """Build engine kwargs. NullPool does not accept pool_size/max_overflow."""
    kwargs: dict = {"echo": settings.DATABASE_ECHO, "pool_pre_ping": True}
    if _is_sqlite:
        kwargs["poolclass"] = NullPool
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["poolclass"] = QueuePool
        kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
        kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
        kwargs["pool_timeout"] = settings.DATABASE_POOL_TIMEOUT
        kwargs["pool_recycle"] = settings.DATABASE_POOL_RECYCLE
        if _is_postgres:
            kwargs["connect_args"] = {
                "connect_timeout": 10,
                "application_name": settings.APP_NAME,
            }
    return kwargs


engine = create_engine(settings.DATABASE_URL, **_build_engine_kwargs())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def drop_db() -> None:
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)


@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, connection_record):
    if _is_sqlite:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    elif _is_postgres:
        cursor = dbapi_conn.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"Database connection check failed: {e}")
        return False
