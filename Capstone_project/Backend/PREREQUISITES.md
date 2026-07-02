# Skeptic Engine — Real-Time Backend Prerequisites

What you need in place before (and while) building out the real-time backend.

## 1. Infrastructure / services

| Service | Why | Local (docker-compose) | Notes |
|---|---|---|---|
| PostgreSQL 16 | Primary store: cases, states, transcripts, evidence, audit | `postgres` service, port 5432 | Enable the `pgvector` extension if you use the RAG embeddings table |
| Redis 7 | Celery broker/result backend **and** the real-time pub/sub bridge | `redis` service, port 6379 | DB 0 cache, DB 1 broker, DB 2 results, plus pub/sub channels |
| EventStoreDB 23.10 | Immutable, append-only audit trail | `eventstore` service, port 2113 (gRPC) | Optional — the app falls back to a Postgres hash-chain if it is down |
| Celery worker + beat | Runs investigations off the request thread; scheduled cleanup | `worker`, `beat` services | The worker is where the agent crew actually executes |
| Flower | Celery monitoring UI | `flower` service, port 5555 | Optional but handy |

All of these are already wired in `docker-compose.yml`. `docker compose up -d` gives you the full stack.

## 2. Accounts / secrets

- **Anthropic API key** — required only when `USE_REAL_AGENTS=true`. Put it in `.env` as `ANTHROPIC_API_KEY`. With the default `false`, the pipeline runs deterministic stubs so you can develop the plumbing without spending tokens.
- **SECRET_KEY** — change from the default before any shared/staging deploy; it signs JWTs.
- Confirm the Claude model IDs in `.env` are current for your account (`CLAUDE_MODEL_REASONING`, `CLAUDE_MODEL_LIGHTWEIGHT`).

## 3. Local toolchain

- Python 3.11+ (the Dockerfile uses 3.11-slim).
- `pip install -r requirements.txt` (ideally in a virtualenv).
- Docker + Docker Compose for the backing services.
- `psql` / `redis-cli` are useful for poking at state.

## 4. Decisions to make before going further

1. **Real agents vs. stubs.** The executor currently streams real WebSocket events but uses stubbed agent output unless `USE_REAL_AGENTS=true`. Flip it on once you have an API key and want real Claude reasoning. Cost and latency go up materially (5 LLM calls × debate rounds per case).
2. **Evidence sourcing.** `collect_evidence_task` and the Evidence agent return placeholder data. You'll need real connectors (policy KB / vector search, vendor registry API, FX API) before output is trustworthy.
3. **Migrations strategy.** `Base.metadata.create_all()` is fine for dev, but use Alembic for anything shared. Scaffold is in `migrations/`; generate the first revision with `alembic revision --autogenerate -m "init"` against a running Postgres.
4. **AuthN/AuthZ depth.** JWT login exists, but there's no user-registration endpoint or role enforcement on routes yet. Decide how users get provisioned and which roles gate which actions.
5. **Frontend contract.** The UI currently uses mock data. Agree on the REST + WebSocket event shapes (see `websocket_manager.py` event classes) so the React app can bind to the live API.

## 5. How the real-time path actually works (important)

The worker and the API run in **separate processes**, so an in-memory broadcaster can't reach WebSocket clients. The flow is:

```
Celery worker → InvestigationExecutor._emit()
     ├─ redis_bus.publish_event()  → Redis channel "investigation_events:{id}"
     └─ connection_manager.broadcast()  (same-process clients only)

FastAPI WS endpoint → redis_bus.subscribe_events() → forwards to the browser
```

So Redis must be reachable from both processes for live updates to flow end-to-end.

## 6. Quick start

```bash
cp .env.example .env          # then fill ANTHROPIC_API_KEY, SECRET_KEY
docker compose up -d          # postgres, redis, eventstore, api, worker, beat, flower
# API docs:        http://localhost:8000/docs
# Flower:          http://localhost:5555
# create a case via POST /api/v1/investigations, then POST .../{id}/execute
# open ws://localhost:8000/api/v1/ws/investigations/{id} to watch it live
```

To run without Docker (stub mode):

```bash
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./dev.db AUTH_REQUIRED=false USE_REAL_AGENTS=false
uvicorn main:app --reload
pytest        # 14 tests, no external services needed
```
