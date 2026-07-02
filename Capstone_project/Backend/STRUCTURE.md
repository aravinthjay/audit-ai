# Backend Project Structure

Real-time multi-agent AI audit platform — FastAPI backend, organized as an
installable `app/` package with domain-grouped subpackages.

```
Backend/
├── app/                              # application package
│   ├── main.py                       # FastAPI app factory (create_app) + lifespan
│   │
│   ├── core/                         # cross-cutting concerns
│   │   ├── config.py                 # pydantic-settings (env-aware Settings)
│   │   └── security.py               # password hashing + JWT + get_current_user
│   │
│   ├── api/
│   │   └── routes/                   # HTTP/WS routers (included by main)
│   │       ├── health.py             # /health, /health/detailed
│   │       ├── auth.py               # /api/v1/auth/token
│   │       ├── investigations.py     # /api/v1/investigations (CRUD + execute)
│   │       └── websocket.py          # /api/v1/ws/investigations/{id}
│   │
│   ├── schemas/                      # Pydantic request/response models
│   │   └── __init__.py
│   │
│   ├── db/
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   └── session.py                # engine, SessionLocal, get_db_session
│   │
│   ├── agents/
│   │   ├── crew.py                   # LangGraph 6-agent crew + state machine
│   │   └── executor.py               # InvestigationExecutor (pipeline + streaming)
│   │
│   ├── realtime/
│   │   ├── websocket_manager.py      # in-process connection manager + events
│   │   └── redis_bus.py              # cross-process pub/sub bridge
│   │
│   ├── tasks/
│   │   └── celery_app.py             # Celery app, tasks, beat schedule
│   │
│   └── audit/
│       └── eventstore.py             # EventStoreDB + Postgres hash-chain fallback
│
├── migrations/                       # Alembic (env.py wired to app.db.models.Base)
│   ├── env.py · script.py.mako · versions/
│
├── tests/                            # pytest (sqlite, stub agents — no services)
│   ├── conftest.py
│   ├── test_api.py · test_auth.py · test_agents.py
│   ├── test_executor.py · test_audit.py
│
├── main.py                           # compat shim -> `from app.main import app`
├── Dockerfile                        # CMD: uvicorn app.main:app
├── docker-compose.yml                # api / worker / beat / flower + datastores
├── k8s-deployment.yaml
├── requirements.txt · pyproject.toml · alembic.ini · .env.example
└── docs: README · QUICKSTART · STRUCTURE · PREREQUISITES · BACKEND_FIXES
```

## Module entrypoints

| Process | Command |
|---|---|
| API server | `uvicorn app.main:app` (or `main:app` via the shim) |
| Celery worker | `celery -A app.tasks.celery_app worker` |
| Celery beat | `celery -A app.tasks.celery_app beat` |
| Migrations | `alembic revision --autogenerate -m "init"` then `alembic upgrade head` |
| Tests | `pytest` (14 tests, no external services) |

## Import map (old flat module -> new path)

```
config                  -> app.core.config
auth                    -> app.core.security
schemas                 -> app.schemas
db_models               -> app.db.models
db_session              -> app.db.session
agent_crew              -> app.agents.crew
investigation_executor  -> app.agents.executor
websocket_manager       -> app.realtime.websocket_manager
redis_bus               -> app.realtime.redis_bus
celery_config           -> app.tasks.celery_app
eventstore_client       -> app.audit.eventstore
```

## Request / data flow

```
Client ──HTTP──> app.api.routes.investigations ──> app.db (Postgres)
        │                       │
        │                       └─ POST /execute ──> Celery (app.tasks.celery_app)
        │                                                   │
        └──WebSocket── app.api.routes.websocket             ▼
                          ▲                     app.agents.executor
                          │                       ├─ app.agents.crew (LLM agents)
              app.realtime.redis_bus  <───────────┤  emits events
              (Redis pub/sub bridge)              ├─ app.db  (state, transcripts)
                                                  └─ app.audit.eventstore (audit trail)
```
