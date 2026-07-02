# Quick Start Guide - Skeptic Engine Backend

Get the real-time backend running in **5 minutes**.

---

## 🚀 Start (Docker Compose)

### Step 1: Setup Environment (1 minute)

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add the API key for your selected default provider:
```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-v1-your-key-here
# Optional fallbacks:
GROQ_API_KEY=
OPENAI_API_KEY=
ENABLE_LLM_FALLBACK=true
LLM_FALLBACK_ORDER=groq,openai
```

### Step 2: Start Services (1 minute)

```bash
docker-compose up -d
```

Wait for all containers to be healthy:
```bash
docker-compose ps
# Should show 7 services: api, postgres, redis, eventstore, worker, beat, flower
```

### Step 3: Verify (1 minute)

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs

# Celery monitoring
open http://localhost:5555

# EventStoreDB
open http://localhost:2113
```

### Step 4: Create & Execute an Investigation (1 minute)

```bash
# Create
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-001",
    "vendor": "Acme Corp",
    "category": "Consulting",
    "amount": 75000
  }')

INVESTIGATION_ID=$(echo $RESPONSE | jq -r '.id')

# Execute (async via Celery)
curl -X POST http://localhost:8000/api/v1/investigations/$INVESTIGATION_ID/execute

echo "Investigation ID: $INVESTIGATION_ID"
```

### Step 5: Monitor in Real-Time

**Option 1: Flower (Celery UI)**
- Open: http://localhost:5555
- See: Task queue, worker status, execution history

**Option 2: WebSocket (Live Updates)**

```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/investigations/YOUR_INVESTIGATION_ID');
ws.onmessage = (event) => {
  console.log('Update:', JSON.parse(event.data));
};
```

**Option 3: API Polling**

```bash
curl http://localhost:8000/api/v1/investigations/$INVESTIGATION_ID
```

---

## 📊 What's Running

After `docker-compose up`:

| Service | Port | Purpose |
|---------|------|---------|
| FastAPI | 8000 | REST + WebSocket API |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache & task broker |
| EventStoreDB | 2113 | Immutable audit log |
| Celery Worker | - | Async task execution |
| Celery Beat | - | Scheduled tasks |
| Flower | 5555 | Task monitoring |

---

## 🔌 API Endpoints

### Create Investigation
```bash
POST /api/v1/investigations
Content-Type: application/json

{
  "transaction_id": "TXN-001",
  "vendor": "Acme Corp",
  "category": "Consulting",
  "amount": 75000
}
```

### List Investigations
```bash
GET /api/v1/investigations?risk=high&status=intake&skip=0&limit=10
```

### Get Details
```bash
GET /api/v1/investigations/{investigation_id}
```

### Start Execution
```bash
POST /api/v1/investigations/{investigation_id}/execute
```

### WebSocket Stream
```
ws://localhost:8000/api/v1/ws/investigations/{investigation_id}
```

---

## 🛑 Stop Services

```bash
docker-compose down
```

---

## 🧹 Cleanup

```bash
# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# View logs before cleanup
docker-compose logs > backup.log
```

---

## 🔥 Common Tasks

### View Logs

```bash
# API logs
docker-compose logs api -f

# Worker logs
docker-compose logs worker -f

# All logs
docker-compose logs -f
```

### Restart a Service

```bash
docker-compose restart api        # Restart API
docker-compose restart worker     # Restart worker
docker-compose restart postgres   # Restart database
```

### Reset Database

```bash
docker-compose down
docker volume rm backend_postgres_data
docker-compose up -d postgres
```

### SSH into Container

```bash
# API container
docker-compose exec api /bin/bash

# Database
docker-compose exec postgres psql -U skeptic -d skeptic_engine
```

---

## 🐛 Troubleshooting

### "Connection refused" on http://localhost:8000

```bash
# Check if container is running
docker-compose ps

# Check logs
docker-compose logs api

# Restart
docker-compose restart api
```

### Database won't start

```bash
# Check logs
docker-compose logs postgres

# Reset
docker-compose down -v
docker-compose up postgres -d
```

### Celery tasks not executing

```bash
# Check worker is running
docker-compose logs worker | grep "ready to accept tasks"

# Restart worker
docker-compose restart worker

# Monitor in Flower
open http://localhost:5555
```

### Port already in use

```bash
# Find process using port 8000
lsof -i :8000

# Kill and restart
docker-compose restart api
```

---

## 📚 Next Steps

1. **Read the full README**: `backend/README.md`
2. **Explore API docs**: http://localhost:8000/docs
3. **Watch Celery**: http://localhost:5555
4. **Check events**: http://localhost:2113
5. **Read the code**: Start with `main.py`

---

## 🎯 What's Happening

When you create an investigation:

```
1. API creates record in PostgreSQL
2. API queues task in Redis
3. Celery worker picks up task
4. LangGraph crew executes 5 phases:
   - Phase 1: Supervisor orchestrates
   - Phase 2: Evidence agent collects
   - Phase 3: Challenger/Defender debate
   - Phase 4: Verifier QA-gates
   - Phase 5: Adjudicator renders verdict
5. WebSocket broadcasts live updates
6. EventStoreDB logs immutable audit trail
7. Investigation marked complete
```

Monitor each step in Flower (http://localhost:5555)

---

## 💡 Tips

- **Use Flower** for production monitoring
- **Use WebSocket** for real-time UI updates
- **Check EventStoreDB** for audit compliance
- **Keep logs** for debugging
- **Scale workers** by changing `docker-compose.yml`

---

**You're ready! Start creating investigations →**

```bash
INVESTIGATION_ID=$(curl -s -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-001",
    "vendor": "Acme",
    "category": "Services",
    "amount": 100000
  }' | jq -r '.id')

curl -X POST http://localhost:8000/api/v1/investigations/$INVESTIGATION_ID/execute
```

Boom. 🚀
