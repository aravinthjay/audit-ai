"""Compatibility shim — the app now lives in app/main.py.

Kept so `uvicorn main:app` still works; prefer `uvicorn app.main:app`.
"""

from app.main import app  # noqa: F401
