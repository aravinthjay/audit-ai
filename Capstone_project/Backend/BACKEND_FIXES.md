# Backend Audit & Fixes

Full-pass review of the `Backend/` folder. Below is every flaw found and what was
changed. Verified with 14 passing tests + import smoke test (SQLite, stub agents,
no external services).

## Critical — app could not start or would crash at runtime

1. **`db_models.py` — reserved `metadata` column.** `VectorEmbedding.metadata` is a
   name reserved by SQLAlchemy's declarative API; defining it raises
   `InvalidRequestError` at import, taking down the whole app. → Renamed the
   attribute to `meta` (mapped to a `meta` DB column).

2. **Raw SQL not wrapped in `text()`.** `db.execute("SELECT 1")` in the health
   check and `db_session.check_db_connection()` raises `ObjectNotExecutableError`
   on SQLAlchemy 2.0. → Wrapped in `sqlalchemy.text()`.

3. **`db_session.py` — NullPool + pool kwargs.** The SQLite branch set
   `poolclass=NullPool` while still passing `pool_size`/`max_overflow`/
   `pool_timeout`, which `NullPool` rejects (`TypeError`). → Pool sizing args are
   now only passed for the pooled (PostgreSQL) backend.

4. **Enum not JSON-serializable in broadcasts.** `_phase_report_and_audit` put a
   `RiskLevel` enum into a WebSocket payload; `json.dumps` then throws. → Emit
   `.value`, and `json.dumps(..., default=str)` everywhere as a safety net.

5. **Celery async execution bug.** `asyncio.get_event_loop().run_until_complete(...)`
   raises in a worker thread on Python 3.10+. → Switched to `asyncio.run(...)`.

## High — real-time / agents didn't actually work

6. **Worker broadcasts never reached clients.** The executor runs in the Celery
   worker process; `connection_manager` lives in the API process, so events went
   nowhere. → Added `redis_bus.py` (Redis pub/sub). Executor publishes events;
   the WebSocket endpoint subscribes and forwards them to the browser.

7. **Debate would infinite-loop.** `route_debate` checked `debate_round` but
   nothing incremented it within the challenger→defender cycle, so the compiled
   graph could loop forever. → `debate_round` is now incremented in the defender
   node; added tests proving the loop terminates.

8. **Agent crew was dead code.** The graph was compiled but never invoked; the
   executor used `asyncio.sleep` + hardcoded verdicts. → Executor now invokes the
   real agent nodes when `USE_REAL_AGENTS=true` (off-thread via `asyncio.to_thread`)
   and persists evidence, debate transcripts, and verification claims to the DB.
   Stubs remain for keyless local/CI runs.

9. **ChatAnthropic missing key/tokens.** Clients were built without `api_key` or
   `max_tokens`. → Both passed from settings; heavy imports made lazy so the app
   boots without `langgraph`/`langchain` installed.

## Medium — correctness, API design, data model

10. **`POST /investigations` used query params.** Bare function args became required
    query parameters instead of a JSON body. → Added `schemas.py` Pydantic models;
    the route now takes a validated `InvestigationCreate` body and returns typed
    responses (HTTP 201).

11. **No "failed" state.** Failures set status to `CLOSED`. → Added
    `InvestigationStatus.FAILED` and an `error_message` column; failures now roll
    back, mark `FAILED`, and record the error.

12. **`TrustedHostMiddleware` hardcoded to localhost.** Would 400 every request in
    Docker/prod. → Driven by `settings.ALLOWED_HOSTS`.

13. **Fake audit hash chain.** `verify_chain_integrity` computed hashes and threw
    them away. → Real SHA256 chain (each row's hash covers the previous hash +
    a per-investigation `sequence`); a test tampers a row and confirms detection.

14. **Wrong EventStore client + port.** Code imported the unmaintained `esdb`
    package; compose pointed at the legacy TCP port 1113. → Rewrote against
    maintained `esdbclient`, lazy-imported, with a graceful **Postgres hash-chain
    fallback** when EventStore is unavailable. Compose now uses gRPC port 2113.

15. **Pydantic v1 config style.** `class Config` is deprecated in pydantic v2 and
    list env-vars failed to parse. → `SettingsConfigDict` + a validator that
    accepts JSON lists or comma-separated strings for `CORS_ORIGINS`/`ALLOWED_HOSTS`.

16. **Duplicate connect listener.** `main.py` registered a second SQLite PRAGMA
    `connect` listener already handled in `db_session.py`. → Removed.

## Low — packaging, deps, hygiene

17. **`requirements.txt`** — removed the bogus `asyncio-contextmanager`; replaced
    `esdb` with `esdbclient`; bumped stale pins (langgraph 0.0.48 → 0.2.x,
    langchain 0.1 → 0.3, fastapi/sqlalchemy/pydantic/redis/celery to current).
18. **`pyproject.toml`** — `packages = ["app"]` referenced a non-existent package
    (build would fail). → Switched to the real flat `py-modules` list.
19. **`.env.example`** — documented new flags: `USE_REAL_AGENTS`, `AUTH_REQUIRED`,
    `ALLOWED_HOSTS`, `AUDIT_FALLBACK_TO_POSTGRES`.

## New files added

- `schemas.py` — Pydantic request/response models.
- `auth.py` — password hashing + JWT (OAuth2 password bearer); `User` model + login route.
- `redis_bus.py` — Redis pub/sub bridge for cross-process real-time events.
- `migrations/` — Alembic scaffold (`env.py` wired to `Base.metadata`).
- `tests/` — `conftest.py` + 14 tests (API, auth, agent routing, full executor pipeline, audit chain).

## Verified

```
14 passed in ~2.6s        # pytest, SQLite + stub agents, no external services
all modules import + py_compile clean
```

## Still open (intentionally out of scope for this pass)

- Real evidence connectors (policy KB / vector search, registry API, FX) — still stubs.
- Generate the first Alembic migration against a live Postgres.
- User-registration endpoint + per-route role enforcement.
- Report generation (`generate_report_task`) is a placeholder path.
- Verify the exact `esdbclient` append/read signatures against your EventStoreDB
  version when you enable it (the Postgres fallback is fully tested; the ESDB path
  is best-effort and guarded).
