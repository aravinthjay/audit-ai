# Local Production-Like Stack

This setup keeps your existing local PostgreSQL database and runs only the extra
production services locally: Redis, Celery, EventStoreDB, and real LLM
agents.

## 1. Start Redis and EventStoreDB

Docker path:

```powershell
cd "C:\Users\athit\Skeptic Engine\Backend"
docker compose -f docker-compose.local-infra.yml up -d
```

If Docker is not installed, install Docker Desktop first, or install Redis and
EventStoreDB natively and expose:

- Redis: `localhost:6379`
- EventStoreDB gRPC/http: `localhost:2113`

## 2. Configure `.env`

Copy the production-like local template:

```powershell
cd "C:\Users\athit\Skeptic Engine\Backend"
Copy-Item .env.local-production.example .env
```

Then edit `.env` and replace:

```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-v1-replace-with-your-local-key
# Optional fallbacks:
GROQ_API_KEY=
OPENAI_API_KEY=
ENABLE_LLM_FALLBACK=true
LLM_FALLBACK_ORDER=groq,openai
```

Keep these values enabled for the full local stack:

```env
USE_REDIS_EVENTS=true
USE_CELERY=true
USE_EVENTSTORE=true
USE_REAL_AGENTS=true
```

## 3. Run the preflight check

```powershell
cd "C:\Users\athit\Skeptic Engine\Backend"
.\.venv\Scripts\python.exe scripts\check_local_stack.py
```

All rows should show `OK` before you run real-agent investigations.

## 4. Start the API

Terminal 1:

```powershell
cd "C:\Users\athit\Skeptic Engine\Backend"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5. Start Celery worker

Terminal 2:

```powershell
cd "C:\Users\athit\Skeptic Engine\Backend"
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

`--pool=solo` is recommended on Windows.

## 6. Optional Celery dashboard

Terminal 3:

```powershell
cd "C:\Users\athit\Skeptic Engine\Backend"
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app flower --port=5555
```

Open `http://localhost:5555`.

## 7. Start UI

Terminal 4:

```powershell
cd "C:\Users\athit\Skeptic Engine\Ui"
pnpm dev
```

Open `http://localhost:3000`.

## 8. Smoke test one case

Use the UI:

1. Open `http://localhost:3000/investigations`.
2. Open one `intake` case.
3. Click `Run crew`.
4. Watch the Celery worker terminal.
5. Refresh evidence, debate, verification, and audit panels.

Do not run all 100 sample cases with `USE_REAL_AGENTS=true` until you are happy
with cost and latency. Each case makes multiple LLM calls. Token/cost telemetry
appears in the UI Analytics page and through `/api/v1/analytics/llm/*`.
