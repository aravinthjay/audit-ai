# Skeptic Engine - Real-Time Backend

**Production-grade real-time multi-agent AI audit investigation platform backend**

Built with FastAPI, PostgreSQL, LangGraph, Celery, and EventStoreDB for immutable audit trails.

---

## 🏗️ Project Structure

```
backend/
├── main.py                      # FastAPI app entry point + WebSocket routes
├── config.py                    # Environment settings & configuration
├── db_session.py               # Database connection pooling
├── db_models.py                # SQLAlchemy ORM models
├── websocket_manager.py        # WebSocket connection & event management
├── agent_crew.py               # LangGraph multi-agent orchestration
├── investigation_executor.py   # Investigation execution engine
├── celery_config.py            # Celery task queue & workers
├── eventstore_client.py        # EventStoreDB audit trail
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image
├── docker-compose.yml          # Local dev stack (7 services)
├── k8s-deployment.yaml         # Kubernetes manifests
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- At least one LLM provider API key when `USE_REAL_AGENTS=true` (Anthropic, Groq, or OpenAI)

### Option 1: Local Development (Docker Compose)

1. **Setup environment**

   ```bash
   cd backend
   cp .env.example .env
   # Edit .env and add the API key for your DEFAULT_LLM_PROVIDER
   ```

2. **Start services**

   ```bash
   docker-compose up -d
   ```

3. **Verify**

   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # API docs
   open http://localhost:8000/docs
   
   # Monitoring
   open http://localhost:5555  # Flower (Celery)
   open http://localhost:2113  # EventStoreDB
   ```

### Option 2: Local Development (Direct Python)

1. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start PostgreSQL, Redis, EventStoreDB** (using Docker)

   ```bash
   docker-compose up postgres redis eventstore -d
   ```

4. **Start FastAPI**

   ```bash
   uvicorn main:app --reload
   ```

5. **Start Celery (in another terminal)**

   ```bash
   celery -A app.tasks.celery_app worker --loglevel=info --pool=solo 
   ```

---

## 🔌 API Usage

### Create Investigation

```bash
curl -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-001",
    "vendor": "Acme Corp",
    "category": "Consulting",
    "amount": 75000
  }'
```

### List Investigations

```bash
curl http://localhost:8000/api/v1/investigations?risk=high&status=intake
```

### Get Investigation Details

```bash
curl http://localhost:8000/api/v1/investigations/{investigation_id}
```

### Start Execution (Async)

```bash
curl -X POST http://localhost:8000/api/v1/investigations/{investigation_id}/execute
```

### Third-Party Evidence Verification

Claim uploads are stored as investigations, and the claim verification API uses
the investigation id as `claimId`.

```bash
# Manually re-run third-party benchmark verification for a claim
curl -X POST http://localhost:8000/api/v1/claims/{claimId}/verify-evidence \
  -H "Content-Type: application/json" \
  -d '{
    "category": "flight",
    "claimed_amount": 20000,
    "route_from": "Puducherry",
    "route_to": "Bengaluru",
    "service_date": "2026-07-10",
    "currency": "INR"
  }'

# Fetch the latest stored verification result
curl http://localhost:8000/api/v1/claims/{claimId}/verification

# Preview before creating a claim
curl -X POST http://localhost:8000/api/v1/claims/verify-preview \
  -H "Content-Type: application/json" \
  -d '{"category":"fuel","claimed_amount":1050,"quantity":10}'
```

Response shape:

```json
{
  "id": "evidence-verification-id",
  "claim_id": "claim-id",
  "category": "flight",
  "claimed_amount": 20000,
  "fetched_amount": 7500,
  "min_acceptable_amount": 5625,
  "max_acceptable_amount": 9375,
  "difference_amount": 12500,
  "difference_percentage": 1.666667,
  "tolerance_percentage": 0.25,
  "provider_name": "live_flight_fare_api",
  "provider_reference_id": "LIVE-FLIGHT-123",
  "verification_status": "FLAGGED",
  "confidence_score": 0.78,
  "reason": "Claimed amount is outside the accepted +/-25% range.",
  "created_at": "2026-06-30T08:00:00Z",
  "updated_at": "2026-06-30T08:00:00Z"
}
```

Statuses are `VERIFIED`, `FLAGGED`, `API_UNAVAILABLE`, and
`NEEDS_MANUAL_REVIEW`. The raw provider response is stored in the database for
audit/debugging but is not returned to the UI.

### WebSocket Real-Time Updates

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/api/v1/ws/investigations/{investigation_id}'
);

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(update.type, update.message);
  // Types: agent_status, debate_message, pipeline_stage, verification
};
```

---

## 🤖 Multi-Agent Crew

### Agents (LangGraph)

1. **Supervisor** - Orchestrates workflow pipeline
2. **Evidence Agent** - Collects data from RAG + external APIs
3. **Challenger** (Red Team) - Argues worst-case risk
4. **Defender** (Blue Team) - Argues legitimate rationale
5. **Adjudicator** - Weighs debate, renders risk verdict
6. **Verifier** - QA-gates claims for grounding

### Workflow Phases

```
PHASE 1: INTAKE
  ↓
PHASE 2: EVIDENCE COLLECTION
  ↓
PHASE 3: DEBATE (≤2 rounds)
  Challenger ↔ Defender
  ↓
PHASE 4: VERIFICATION
  Verifier QA-gates claims
  ↓
PHASE 5: DECISION + AUDIT LOG
  Risk verdict + immutable log
  ↓
CLOSED
```

---

## 💾 Database

### PostgreSQL Tables

- **investigations** - Case metadata
- **investigation_states** - LangGraph state checkpoints
- **debate_transcripts** - Debate messages
- **evidence_artifacts** - Collected evidence
- **verification_claims** - Verified claims
- **third_party_evidence_verifications** - Claim amount benchmark checks
- **runtime_settings** - Persisted provider routing settings from the UI
- **llm_call_logs** - LLM token, cost, latency, fallback, cache, and routing telemetry
- **audit_log** - Audit trail (legacy)
- **review_queue** - Human review queue
- **vector_embeddings** - RAG embeddings

### EventStoreDB

Immutable event stream (one stream per investigation):
- Stream name: `investigations-{investigation_id}`
- Events: case_created, debate_completed, case_approved, etc.
- Hash-chain verification

---

## ⚙️ Configuration

All settings via `.env` file (see `.env.example`):

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/skeptic_engine

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# EventStoreDB
EVENTSTORE_URL=esdb://localhost:2113?tls=false

# LLM providers
ANTHROPIC_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=
DEFAULT_LLM_PROVIDER=anthropic
ENABLE_LLM_FALLBACK=true
LLM_FALLBACK_ORDER=groq,openai
LLM_PRICING_OVERRIDES_JSON=
CLAUDE_MODEL_REASONING=claude-3-5-sonnet-20241022
GROQ_MODEL_REASONING=llama-3.3-70b-versatile
OPENAI_MODEL_REASONING=gpt-4.1

# Investigation Defaults
MAX_DEBATE_ROUNDS=2
DEFAULT_MATERIALITY_THRESHOLD=50000.0

# Third-party evidence verification
EVIDENCE_VERIFICATION_DEFAULT_TOLERANCE=0.30
EVIDENCE_VERIFICATION_FLIGHT_TOLERANCE=0.25
EVIDENCE_VERIFICATION_FUEL_TOLERANCE=0.10
FLIGHT_PRICE_PROVIDER_URL=
FLIGHT_PRICE_PROVIDER_API_KEY=
HOTEL_PRICE_PROVIDER_URL=
HOTEL_PRICE_PROVIDER_API_KEY=
FOOD_BENCHMARK_PROVIDER_URL=
FOOD_BENCHMARK_PROVIDER_API_KEY=
CAB_FARE_PROVIDER_URL=
CAB_FARE_PROVIDER_API_KEY=
FUEL_PRICE_PROVIDER_URL=
FUEL_PRICE_PROVIDER_API_KEY=
GST_VERIFICATION_PROVIDER_URL=
GST_VERIFICATION_PROVIDER_API_KEY=
```

Provider URLs must point at real third-party APIs or approved internal wrapper
services that normalize each provider response into `reference_amount`,
`provider_name`, `provider_reference_id`, `confidence`, and `reason`. Empty
provider URLs and provider timeouts are recorded as `API_UNAVAILABLE` and do not
block claim creation.

### LLM Provider Routing, Fallback, and Cost Tracking

The real-agent path uses a provider abstraction under `app/llm`.

- Supported providers: Anthropic (`ANTHROPIC_API_KEY`), Groq (`GROQ_API_KEY`), and OpenAI (`OPENAI_API_KEY`).
- `DEFAULT_LLM_PROVIDER` controls the first provider used by real agents.
- `ENABLE_LLM_FALLBACK=true` enables retry on token/context limit, rate-limit, timeout, and quota failures.
- `LLM_FALLBACK_ORDER` controls fallback order, for example `groq,openai`.
- `GET /api/v1/settings/llm` returns provider status without secrets.
- `PUT /api/v1/settings/llm` persists default provider, fallback toggle, and fallback order in `runtime_settings`.

Every attempted LLM call is recorded in `llm_call_logs` with provider, model,
request type, input/output/total tokens, estimated cost, actual cost when the
provider returns it, latency, success/failure, fallback metadata, cache hits,
routing reason, guardrail text, and available user/session/request IDs.

LLM analytics endpoints:

- `GET /api/v1/analytics/llm/summary`
- `GET /api/v1/analytics/llm/by-provider`
- `GET /api/v1/analytics/llm/by-model`
- `GET /api/v1/analytics/llm/recent-calls`
- `GET /api/v1/analytics/llm/cost-trends`

Estimated cost uses `app/llm/pricing.py`. Keep model prices current with
`LLM_PRICING_OVERRIDES_JSON`, for example:

```env
LLM_PRICING_OVERRIDES_JSON={"gpt-4.1-mini":{"input_per_million":0.40,"output_per_million":1.60}}
```

Cost optimization keeps quality guardrails in place:

- Duplicate prompt lines are removed and prompts are trimmed to `LLM_MAX_PROMPT_TOKENS`.
- Simple low-risk requests can use lightweight models.
- Audit-critical tasks such as adjudication and verification use reasoning models.
- Cache is used only for explicitly cacheable requests.
- Routing decisions and quality guardrails are logged for review.

Pricing estimates depend on the configured model price table and may differ from
provider invoices if prices, discounts, or billing units change.

---

## 🐳 Docker Services

### Local Development Stack

```bash
docker-compose up -d
```

Services:
- 🔵 **api** - FastAPI (port 8000)
- 🟢 **postgres** - Database (port 5432)
- 🔴 **redis** - Cache & broker (port 6379)
- 📊 **eventstore** - Audit log (port 2113)
- 🐝 **worker** - Celery worker
- ⏰ **beat** - Celery scheduler
- 📈 **flower** - Celery monitoring (port 5555)

### Logs

```bash
docker-compose logs -f api          # Follow API logs
docker-compose logs worker          # Celery worker logs
docker-compose logs postgres        # Database logs
```

### Stop Services

```bash
docker-compose down
```

---

## ☸️ Kubernetes Deployment

### Deploy

```bash
# Set secrets. Pick the provider key that matches DEFAULT_LLM_PROVIDER.
export DEFAULT_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-v1-...
export GROQ_API_KEY=
export OPENAI_API_KEY=
export SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_PASSWORD=$(openssl rand -hex 16)

# Create secrets in cluster
kubectl create secret generic skeptic-secrets \
  --from-literal=DEFAULT_LLM_PROVIDER=$DEFAULT_LLM_PROVIDER \
  --from-literal=ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  --from-literal=GROQ_API_KEY=$GROQ_API_KEY \
  --from-literal=OPENAI_API_KEY=$OPENAI_API_KEY \
  --from-literal=SECRET_KEY=$SECRET_KEY \
  --from-literal=DATABASE_PASSWORD=$DATABASE_PASSWORD \
  -n skeptic-engine

# Apply manifests
kubectl apply -f k8s-deployment.yaml
```

### Monitor

```bash
# Watch rollout
kubectl get pods -n skeptic-engine -w

# Check service status
kubectl get svc -n skeptic-engine

# View logs
kubectl logs -n skeptic-engine deployment/skeptic-api -f

# Port forward
kubectl port-forward -n skeptic-engine svc/skeptic-api 8000:80
```

### Scaling

- **API**: Auto-scales 3-10 replicas on CPU/memory
- **Workers**: Auto-scales 2-5 replicas on CPU
- Manual scaling: `kubectl scale deployment skeptic-api -n skeptic-engine --replicas=5`

---

## 📊 Monitoring

### Flower (Celery Web UI)

```
http://localhost:5555
```

Features:
- Task queue status
- Worker health
- Execution history
- Performance metrics

### EventStoreDB UI

```
http://localhost:2113
```

Features:
- Event streams
- Projections
- Event browser

### Logs

```bash
# API logs
docker-compose logs api

# Celery worker logs
docker-compose logs worker

# All logs
docker-compose logs
```

---

## 🧪 Testing

### Run Tests

```bash
pytest
pytest tests/test_api.py -v
pytest --cov=. --cov-report=html
```

### Example Test

```python
from db_models import Investigation

def test_create_investigation():
    inv = Investigation(
        transaction_id="TXN-001",
        vendor="Acme",
        category="Services",
        amount=100000
    )
    
    assert inv.id is not None
    assert inv.status.value == "intake"
```

---

## 🔐 Security

### Built-in

- ✅ JWT authentication (ready)
- ✅ CORS configuration
- ✅ SQLAlchemy ORM (SQL injection prevention)
- ✅ Environment variables (secrets)
- ✅ Non-root container user
- ✅ Health checks

### Production Checklist

- [ ] Enable HTTPS/TLS
- [ ] Configure JWT auth
- [ ] Set strong SECRET_KEY
- [ ] Enable database SSL
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Set up monitoring alerts
- [ ] Rotate API keys
- [ ] Enable rate limiting

---

## 🐛 Troubleshooting

### API won't start

```bash
# Check database connection
python -c "from db_session import check_db_connection; print(check_db_connection())"

# Check all services are healthy
docker-compose ps
```

### WebSocket connection fails

```bash
# Verify endpoint is running
curl http://localhost:8000/health

# Check logs
docker-compose logs api | grep WebSocket
```

### Celery tasks not running

```bash
# Check worker is running
docker-compose logs worker | grep "ready to accept tasks"

# Check flower UI
open http://localhost:5555

# Restart worker
docker-compose restart worker
```

### Database errors

```bash
# Check database connection
docker-compose logs postgres

# Reset database
python -c "from db_session import init_db; init_db()"

# Reinitialize
docker-compose exec postgres psql -U skeptic -d skeptic_engine -c "SELECT 1"
```

---

## 📖 Documentation

### API Endpoints

See `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc)

### Architecture Decisions

**Why FastAPI?**
- Async support for WebSockets
- Built-in dependency injection
- Auto OpenAPI documentation
- Fast performance

**Why LangGraph?**
- First-class multi-agent orchestration
- State management
- Checkpointing & recovery

**Why EventStoreDB?**
- Immutable event log
- Compliance-ready
- Complete audit trail
- Hash-chain verification

**Why Celery?**
- Distributed task queue
- Async investigation execution
- Retry logic & monitoring
- Integration with Flower

---

## 🚀 Deployment

### Development

```bash
docker-compose up
```

### Staging/Production

```bash
kubectl apply -f k8s-deployment.yaml
```

### Environment Variables

```bash
# Development
ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Production
ENV=production
DEBUG=false
LOG_LEVEL=WARNING
```

---

## 📝 License

MIT License - See LICENSE file

---

## 🆘 Support

- **Issues**: GitHub Issues
- **Docs**: `http://localhost:8000/docs`
- **Monitoring**: `http://localhost:5555` (Flower)
- **Events**: `http://localhost:2113` (EventStoreDB)

---

**Built with ❤️ for enterprise audit investigation**
