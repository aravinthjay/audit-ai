# ============================================================
# EXTENSION A + EXTENSION B
# Rate Limiting + Correlation ID Propagation
# ============================================================

from collections import defaultdict
from datetime import datetime
from fastapi.responses import JSONResponse
from prometheus_client import Counter
import contextvars
import httpx
import uuid
import time

# ============================================================
# EXTENSION A — RATE LIMITING
# ============================================================

RATE_LIMIT = 100        # requests
WINDOW_SECONDS = 60     # 1 minute

# Store request timestamps by client IP
request_store = defaultdict(list)

RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Total number of rate limit violations"
)

# ============================================================
# EXTENSION B — CORRELATION ID PROPAGATION
# ============================================================

# Request-scoped correlation ID storage
correlation_id_ctx = contextvars.ContextVar(
    "correlation_id",
    default=None
)

# ============================================================
# COMBINED MIDDLEWARE
# (Rate Limiting + Logging + Correlation ID)
# ============================================================

@app.middleware("http")
async def logging_and_rate_limit_middleware(
    request: Request,
    call_next
):

    # ---------- Rate Limiting ----------
    client_ip = request.client.host
    now = datetime.utcnow()

    # Remove old requests outside the window
    request_store[client_ip] = [
        ts for ts in request_store[client_ip]
        if (now - ts).total_seconds() < WINDOW_SECONDS
    ]

    # Check request count
    if len(request_store[client_ip]) >= RATE_LIMIT:

        RATE_LIMIT_HITS.inc()

        oldest_request = min(request_store[client_ip])

        retry_after = WINDOW_SECONDS - int(
            (now - oldest_request).total_seconds()
        )

        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "retry_after_seconds": retry_after
            },
            headers={
                "Retry-After": str(retry_after)
            }
        )

    request_store[client_ip].append(now)

    # ---------- Correlation ID ----------
    correlation_id = request.headers.get(
        "X-Correlation-Id",
        str(uuid.uuid4())
    )

    correlation_id_ctx.set(correlation_id)

    start = time.perf_counter()

    log.info(
        "request.started",
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id
    )

    response = await call_next(request)

    elapsed_ms = round(
        (time.perf_counter() - start) * 1000,
        2
    )

    log.info(
        "request.completed",
        path=request.url.path,
        status=response.status_code,
        latency_ms=elapsed_ms,
        correlation_id=correlation_id
    )

    response.headers["X-Correlation-Id"] = correlation_id

    return response

# ============================================================
# HTTPX EVENT HOOK
# Automatically forwards correlation IDs
# ============================================================

async def inject_correlation_id(
    request: httpx.Request
):
    correlation_id = correlation_id_ctx.get()

    if correlation_id:
        request.headers[
            "X-Correlation-Id"
        ] = correlation_id

# Shared HTTP client
async_client = httpx.AsyncClient(
    event_hooks={
        "request": [inject_correlation_id]
    }
)

# ============================================================
# MOCK DOWNSTREAM SERVICE
# ============================================================

@app.get("/mock-downstream")
async def mock_downstream(
    request: Request
):
    return {
        "received_correlation_id":
            request.headers.get(
                "X-Correlation-Id"
            )
    }

# ============================================================
# TEST ENDPOINT
# Demonstrates propagation
# ============================================================

@app.get("/test-propagation")
async def test_propagation():

    response = await async_client.get(
        "http://localhost:8000/mock-downstream"
    )

    return {
        "message":
            "Correlation ID forwarded successfully",
        "downstream_response":
            response.json()
    }

print("Extension A: Rate Limiting Enabled")
print("Extension B: Correlation ID Propagation Enabled")