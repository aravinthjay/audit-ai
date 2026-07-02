# Production CI/CD and Deployment

This repository ships a GitHub Actions pipeline plus a Docker Compose production stack.

## Pipeline

Workflow: `.github/workflows/ci-cd.yml`

On pull requests:
- Backend install, Ruff correctness check, and pytest.
- UI install, lint, typecheck, tests, and Next build.

On pushes to `main`:
- Runs the same checks.
- Builds and publishes backend/UI images to GitHub Container Registry.

On manual `workflow_dispatch`:
- Publishes images.
- SSHes into the production host.
- Copies `docker-compose.production.yml`.
- Pulls images, runs Alembic migrations, and restarts services.

## GitHub Variables

Set repository or environment variable:

- `NEXT_PUBLIC_API_BASE_URL`: public API URL baked into the UI image, for example `https://api.example.com/api/v1`.

## GitHub Secrets

Required for production deploy:

- `PROD_HOST`: production host DNS/IP.
- `PROD_USER`: SSH user.
- `PROD_SSH_KEY`: private key with access to the host.
- `PROD_PORT`: SSH port, optional, defaults to `22`.
- `PROD_DEPLOY_PATH`: host path for the compose file, optional, defaults to `~/skeptic-engine`.
- `GHCR_DEPLOY_USER`: GHCR user for host pulls, optional.
- `GHCR_DEPLOY_TOKEN`: GHCR token for private package pulls, optional when the host can pull public images.

## Host Setup

Install Docker Engine with the Compose plugin. Create the deploy directory and copy `production.env.example` to `.env.production`:

```bash
mkdir -p ~/skeptic-engine
cd ~/skeptic-engine
cp production.env.example .env.production
```

Fill `.env.production` with real values. Minimum required:

- `BACKEND_IMAGE`
- `UI_IMAGE`
- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `DEFAULT_LLM_PROVIDER`: one of `anthropic`, `groq`, or `openai`.
- The API key for the selected default provider: `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, or `OPENAI_API_KEY`.
- Optional fallback keys and order: `ENABLE_LLM_FALLBACK=true`, `LLM_FALLBACK_ORDER=groq,openai`.
- `NEXT_PUBLIC_API_BASE_URL`
- `CORS_ORIGINS`
- `ALLOWED_HOSTS`

The deploy workflow injects the exact image tags for each release, so `BACKEND_IMAGE` and `UI_IMAGE` in `.env.production` are mainly useful for manual operations.

## Manual Deploy

From the production host:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml pull
docker compose --env-file .env.production -f docker-compose.production.yml run --rm migrate
docker compose --env-file .env.production -f docker-compose.production.yml up -d --remove-orphans
```

## Smoke Check

From any machine with network access:

```bash
cd Backend
API_BASE_URL=https://api.example.com UI_BASE_URL=https://app.example.com python scripts/production_smoke.py
```

## Request Logging

Request logging is enabled by default in production:

```env
REQUEST_LOGGING_ENABLED=true
REQUEST_LOG_EXCLUDED_PATHS=["/health","/health/detailed","/docs","/openapi.json","/favicon.ico"]
```

Telemetry is persisted to `request_logs`, exposed through `/api/v1/analytics/requests`, and displayed on the UI analytics page.

## LLM Provider Fallback and Analytics

Production supports Anthropic, Groq, and OpenAI providers. The backend validates
the selected `DEFAULT_LLM_PROVIDER` key when `USE_REAL_AGENTS=true`; fallback
providers are tried only for context/token limit, rate-limit, timeout, and quota
failures.

LLM calls are persisted to `llm_call_logs` with token counts, estimated cost,
latency, fallback status, cache hits, routing reason, and quality guardrail
metadata. The UI Analytics page reads:

- `/api/v1/analytics/llm/summary`
- `/api/v1/analytics/llm/by-provider`
- `/api/v1/analytics/llm/by-model`
- `/api/v1/analytics/llm/recent-calls`
- `/api/v1/analytics/llm/cost-trends`

Model pricing lives in backend config and can be overridden with
`LLM_PRICING_OVERRIDES_JSON`. Treat estimated cost as an operational estimate;
provider invoices may differ when official prices or billing terms change.
