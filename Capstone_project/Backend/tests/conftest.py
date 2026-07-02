"""Shared pytest fixtures.

Configures a throwaway SQLite database and disables auth / real agents so the
suite runs with no external services.
"""

import os
import tempfile

_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_DB_PATH}",
        "AUTH_REQUIRED": "false",
        "USE_REAL_AGENTS": "false",
        "MAX_DEBATE_ROUNDS": "2",
        "SECRET_KEY": "test-secret-key",
        "AUDIT_FALLBACK_TO_POSTGRES": "true",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.models import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.close(_DB_FD)
        os.unlink(_DB_PATH)
    except OSError:
        pass


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
