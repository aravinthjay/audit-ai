"""
support_agent.py  —  Day 18 Lab 2 Extension
============================================
Extends the ordering-agent skeleton into a **customer support agent** with:

  Memory
    - Redis LIST  →  short-term memory  (last N turns, TTL-ed per session)
    - In-process vector store  →  long-term recall  (cosine similarity)

  Tools  (≥ 3, one async-queue-backed)
    1. recall_knowledge   – vector search over the KB  (sync)
    2. check_order_status – SQLite order lookup         (sync)
    3. escalate_to_human  – enqueue a support ticket onto a Redis Stream (ASYNC)
    4. create_refund      – high-value refunds need human approval gate
    5. check_ticket       – poll async ticket status

  Infrastructure
    - Background worker thread draining the ticket stream (consumer group)
    - Dead-letter queue (DLQ) after MAX_RETRIES failures
    - Human-approval gate for refunds above APPROVAL_THRESHOLD
    - Per-call trace spans  →  printed as a table after each turn
    - Retry wrapper with exponential back-off on transient tool errors
    - Prompt-caching header on the system prompt block (cache_control)

  Run modes
    LIVE  – set ANTHROPIC_API_KEY in env, real Claude calls
    MOCK  – no key needed, scripted tool chain exercises every path

Usage
-----
    python support_agent.py                   # interactive REPL
    python support_agent.py --demo            # one scripted demo turn
    python support_agent.py --demo --verbose  # with full trace table

Architecture note is printed at the bottom of a --demo run.
"""

# ─────────────────────────────────────────────────────────────────────────────
# 0.  Imports & config
# ─────────────────────────────────────────────────────────────────────────────
import os, sys, json, uuid, time, math, threading, argparse, textwrap
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import fakeredis        # pip install fakeredis
import numpy as np      # pip install numpy
import sqlite3

# ── Anthropic client (optional — falls back to MOCK) ─────────────────────────
try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LIVE  = _HAS_ANTHROPIC and bool(ANTHROPIC_API_KEY)
MODEL = "claude-sonnet-4-6"

# ── Tunables ─────────────────────────────────────────────────────────────────
SESSION_TTL        = 3600          # seconds — Redis key expiry for short-term memory
MAX_HISTORY        = 20            # messages kept per session
EMBEDDING_DIM      = 16            # toy embedding dimension (real: 1536+)
TOP_K              = 2             # KB docs returned per query
APPROVAL_THRESHOLD = 150.0         # USD — refunds above this need human approval
MAX_TOOL_RETRIES   = 3             # retry attempts on transient errors
RETRY_BASE_DELAY   = 0.2           # seconds (doubles each retry)
MAX_AGENT_STEPS    = 10
DLQ_MAX_RETRIES    = 3             # ticket worker failures before DLQ


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Redis  (fakeredis — swap for redis.Redis.from_url(...) in prod)
# ─────────────────────────────────────────────────────────────────────────────
r = fakeredis.FakeStrictRedis()

TICKET_STREAM = "support:tickets"
TICKET_GROUP  = "ticket-handlers"
DLQ_STREAM    = "support:tickets:dlq"

try:
    r.xgroup_create(TICKET_STREAM, TICKET_GROUP, id="0", mkstream=True)
except Exception:
    pass  # group already exists


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Short-term memory  (Redis LIST per session)
# ─────────────────────────────────────────────────────────────────────────────

def stm_key(session_id: str) -> str:
    return f"stm:{session_id}"


def stm_append(session_id: str, role: str, content: str) -> None:
    """Push one message and trim to MAX_HISTORY; refresh TTL."""
    k = stm_key(session_id)
    r.rpush(k, json.dumps({"role": role, "content": content}))
    r.ltrim(k, -MAX_HISTORY, -1)
    r.expire(k, SESSION_TTL)


def stm_load(session_id: str) -> list[dict]:
    """Return the full message list for the session."""
    return [json.loads(m) for m in r.lrange(stm_key(session_id), 0, -1)]


def stm_clear(session_id: str) -> None:
    r.delete(stm_key(session_id))


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Long-term memory — tiny vector store
#     Uses random pseudo-embeddings so no embedding model is required.
#     Swap _embed() for a real model call in production.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KBDoc:
    doc_id:  str
    text:    str
    meta:    dict = field(default_factory=dict)
    vector:  list = field(default_factory=list)


_KB: list[KBDoc] = []


def _embed(text: str) -> list[float]:
    """
    Deterministic toy embedding: hash chars → unit vector.
    Replace with:  anthropic.Client().embeddings.create(...)
                or openai.embeddings.create(...)
    """
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(text[:64]))
    rng  = np.random.default_rng(seed)
    v    = rng.random(EMBEDDING_DIM).astype(float)
    norm = np.linalg.norm(v)
    return (v / (norm + 1e-9)).tolist()


def kb_add(doc_id: str, text: str, meta: dict = None) -> None:
    _KB.append(KBDoc(doc_id=doc_id, text=text,
                     meta=meta or {}, vector=_embed(text)))


def kb_search(query: str, top_k: int = TOP_K) -> list[dict]:
    if not _KB:
        return []
    qv = np.array(_embed(query))
    scored = []
    for doc in _KB:
        dv    = np.array(doc.vector)
        score = float(np.dot(qv, dv) / (np.linalg.norm(qv) * np.linalg.norm(dv) + 1e-9))
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"doc_id": d.doc_id, "text": d.text,
             "score": round(s, 3), **d.meta}
            for s, d in scored[:top_k]]


# ── Seed knowledge base ───────────────────────────────────────────────────────
_KB_SEED = [
    ("kb-returns",   "Return policy: items can be returned within 30 days of delivery. "
                     "A receipt or order ID is required. Refunds are processed within 5–7 business days."),
    ("kb-shipping",  "Standard shipping takes 3–5 business days. Express shipping (1–2 days) is available "
                     "at checkout for an additional fee. International orders take 7–14 days."),
    ("kb-damaged",   "If your item arrived damaged, please contact support within 48 hours with photos. "
                     "We will arrange a free replacement or full refund at your choice."),
    ("kb-cancel",    "Orders can be cancelled within 1 hour of placement if not yet shipped. "
                     "After dispatch, initiate a return instead."),
    ("kb-warranty",  "All electronics carry a 12-month manufacturer warranty. "
                     "Warranty claims require proof of purchase and must be submitted via the support portal."),
    ("kb-account",   "To reset your password, click 'Forgot password' on the login page. "
                     "Account changes take effect immediately."),
]
for _id, _txt in _KB_SEED:
    kb_add(_id, _txt)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  SQLite orders database
# ─────────────────────────────────────────────────────────────────────────────
db = sqlite3.connect(":memory:", check_same_thread=False)
db.execute("""
    CREATE TABLE orders (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        sku     TEXT,
        qty     INTEGER,
        total   REAL,
        status  TEXT,
        email   TEXT
    )
""")
db.execute("""
    CREATE TABLE refunds (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id   INTEGER,
        amount     REAL,
        reason     TEXT,
        status     TEXT   -- pending_approval | approved | rejected | processed
    )
""")
# Seed some orders
db.executemany(
    "INSERT INTO orders (sku,qty,total,status,email) VALUES (?,?,?,?,?)",
    [
        ("KB-01", 1, 129.0,  "delivered",  "alice@example.com"),
        ("MON-4", 1, 410.0,  "shipped",    "bob@example.com"),
        ("HUB-2", 2,  58.0,  "processing", "carol@example.com"),
        ("KB-01", 3, 387.0,  "delivered",  "dave@example.com"),
    ],
)
db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Human-approval gate  (in-process store; prod → DB / webhook)
# ─────────────────────────────────────────────────────────────────────────────
_pending_approvals: dict[str, dict] = {}


def request_approval(payload: dict) -> str:
    token = uuid.uuid4().hex[:8]
    _pending_approvals[token] = {**payload, "status": "pending",
                                  "created_at": time.time()}
    return token


def approve(token: str) -> bool:
    if token in _pending_approvals and _pending_approvals[token]["status"] == "pending":
        _pending_approvals[token]["status"] = "approved"
        return True
    return False


def reject(token: str, reason: str = "") -> bool:
    if token in _pending_approvals and _pending_approvals[token]["status"] == "pending":
        _pending_approvals[token]["status"] = "rejected"
        _pending_approvals[token]["reject_reason"] = reason
        return True
    return False


def get_approval(token: str) -> dict | None:
    return _pending_approvals.get(token)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Trace span collector
# ─────────────────────────────────────────────────────────────────────────────
_spans: list[dict] = []


def record_span(tool: str, args: dict, result: Any,
                elapsed_ms: float, ok: bool) -> None:
    _spans.append({
        "tool":       tool,
        "args":       args,
        "result":     result,
        "elapsed_ms": round(elapsed_ms, 1),
        "ok":         ok,
    })


def print_trace_table() -> None:
    if not _spans:
        return
    print("\n┌─ Trace spans " + "─" * 55)
    print(f"│ {'#':<3}  {'Tool':<25}  {'ms':>6}  {'OK':>4}  Summary")
    print("│" + "─" * 65)
    for i, s in enumerate(_spans, 1):
        summary = str(s["result"])[:38].replace("\n", " ")
        ok_flag = "✓" if s["ok"] else "✗"
        print(f"│ {i:<3}  {s['tool']:<25}  {s['elapsed_ms']:>6}  {ok_flag:>4}  {summary}")
    print("└" + "─" * 65)
    _spans.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Retry wrapper
# ─────────────────────────────────────────────────────────────────────────────

def with_retry(fn, *args, max_retries=MAX_TOOL_RETRIES,
               base_delay=RETRY_BASE_DELAY, **kwargs):
    """
    Call fn(*args, **kwargs) up to max_retries times.
    Retries only on exceptions — not on logical errors returned in dicts.
    """
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = base_delay * (2 ** attempt)
            print(f"  [retry {attempt+1}/{max_retries}] {fn.__name__} failed: {exc}  — wait {wait:.2f}s")
            time.sleep(wait)


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Tool functions
# ─────────────────────────────────────────────────────────────────────────────

# ── Tool 1: recall_knowledge (sync, vector search) ────────────────────────────
def recall_knowledge(query: str) -> dict:
    """Search the long-term KB for relevant policy/FAQ snippets."""
    hits = kb_search(query, top_k=TOP_K)
    if not hits:
        return {"results": [], "message": "No matching knowledge found."}
    return {"results": hits}


# ── Tool 2: check_order_status (sync, SQLite) ─────────────────────────────────
def check_order_status(order_id: int) -> dict:
    """Look up an order by ID and return its status and total."""
    row = db.execute(
        "SELECT id,sku,qty,total,status,email FROM orders WHERE id=? LIMIT 1",
        (order_id,),
    ).fetchone()
    if not row:
        return {"error": f"Order {order_id} not found."}
    return {
        "order_id": row[0], "sku": row[1], "qty": row[2],
        "total": row[3],    "status": row[4], "email": row[5],
    }


# ── Tool 3: escalate_to_human (ASYNC — Redis Stream) ─────────────────────────
def escalate_to_human(issue: str, session_id: str, priority: str = "normal") -> dict:
    """
    Enqueue a support ticket for a human agent.
    Returns immediately with a job_id; the worker resolves it asynchronously.
    Priority: 'normal' | 'urgent'
    """
    job_id = uuid.uuid4().hex[:8]
    r.xadd(TICKET_STREAM, {
        "job_id":     job_id,
        "issue":      issue,
        "session_id": session_id,
        "priority":   priority,
    })
    r.set(f"ticket:{job_id}", json.dumps({
        "status": "queued", "issue": issue, "priority": priority,
    }))
    return {"job_id": job_id, "status": "queued",
            "message": "Ticket raised. A human agent will follow up shortly."}


# ── Tool 4: create_refund (sync, approval gate for large amounts) ─────────────
def create_refund(order_id: int, amount: float, reason: str) -> dict:
    """
    Initiate a refund.
    Amounts above APPROVAL_THRESHOLD are paused for human approval;
    smaller refunds are auto-approved.
    """
    order = check_order_status(order_id)
    if "error" in order:
        return order
    if amount <= 0 or amount > order["total"] + 0.01:
        return {"error": f"Refund amount ${amount:.2f} is invalid for order total ${order['total']:.2f}."}

    if amount > APPROVAL_THRESHOLD:
        token = request_approval({
            "type":     "refund",
            "order_id": order_id,
            "amount":   amount,
            "reason":   reason,
            "email":    order["email"],
        })
        db.execute(
            "INSERT INTO refunds (order_id,amount,reason,status) VALUES (?,?,?,?)",
            (order_id, amount, reason, "pending_approval"),
        )
        db.commit()
        return {
            "status":         "pending_approval",
            "approval_token": token,
            "message":        (f"Refund of ${amount:.2f} exceeds ${APPROVAL_THRESHOLD:.0f} threshold "
                               f"and requires manager approval. Token: {token}"),
        }

    # Auto-approve small refunds
    db.execute(
        "INSERT INTO refunds (order_id,amount,reason,status) VALUES (?,?,?,?)",
        (order_id, amount, reason, "processed"),
    )
    db.commit()
    return {
        "status":  "processed",
        "amount":  amount,
        "message": f"Refund of ${amount:.2f} for order {order_id} processed automatically.",
    }


# ── Tool 5: check_ticket (sync, polls Redis result key) ──────────────────────
def check_ticket(job_id: str) -> dict:
    """Check the status of an escalated support ticket."""
    raw = r.get(f"ticket:{job_id}")
    if not raw:
        return {"error": f"No ticket found for job_id {job_id}."}
    data = json.loads(raw)
    return {"job_id": job_id, **data}


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Tool dispatch + run_tool (with tracing + retry)
# ─────────────────────────────────────────────────────────────────────────────
TOOLS_REGISTRY = {
    "recall_knowledge":    recall_knowledge,
    "check_order_status":  check_order_status,
    "escalate_to_human":   escalate_to_human,
    "create_refund":       create_refund,
    "check_ticket":        check_ticket,
}

TOOL_SCHEMAS = [
    {
        "name":        "recall_knowledge",
        "description": (
            "Search the internal knowledge base for return policies, shipping info, "
            "warranty terms, and other FAQs. Always call this first before answering "
            "a policy question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Natural-language question or topic to search for."},
            },
            "required": ["query"],
        },
    },
    {
        "name":        "check_order_status",
        "description": "Look up an order by its numeric order ID and return status, SKU, and total.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "The numeric order ID."},
            },
            "required": ["order_id"],
        },
    },
    {
        "name":        "escalate_to_human",
        "description": (
            "Escalate an unresolved issue to a human support agent by raising a ticket. "
            "Returns a job_id immediately; resolution happens asynchronously. "
            "Use when the customer's problem cannot be solved with available tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "issue":      {"type": "string",
                               "description": "Clear description of the customer's unresolved issue."},
                "session_id": {"type": "string",
                               "description": "The current session ID for context."},
                "priority":   {"type": "string", "enum": ["normal", "urgent"],
                               "description": "Ticket priority. Use 'urgent' for damaged goods or billing errors."},
            },
            "required": ["issue", "session_id"],
        },
    },
    {
        "name":        "create_refund",
        "description": (
            "Initiate a refund for a delivered or cancelled order. "
            "Refunds above $150 are automatically paused and require manager approval "
            "— you will receive an approval_token to share with the customer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "Order to refund."},
                "amount":   {"type": "number",  "description": "Refund amount in USD (must be ≤ order total)."},
                "reason":   {"type": "string",  "description": "Reason for the refund."},
            },
            "required": ["order_id", "amount", "reason"],
        },
    },
    {
        "name":        "check_ticket",
        "description": "Poll the status of a previously escalated support ticket by its job_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The job_id returned by escalate_to_human."},
            },
            "required": ["job_id"],
        },
    },
]


def run_tool(name: str, args: dict) -> tuple[Any, bool]:
    """
    Dispatch a tool call, record a trace span, and return (result, is_error).
    Wraps execution in the retry helper for transient failures.
    """
    fn = TOOLS_REGISTRY.get(name)
    if not fn:
        err = {"error": f"Unknown tool: {name}"}
        record_span(name, args, err, 0, False)
        return err, True

    t0 = time.monotonic()
    try:
        result   = with_retry(fn, **args)
        elapsed  = (time.monotonic() - t0) * 1000
        is_error = isinstance(result, dict) and "error" in result
        record_span(name, args, result, elapsed, not is_error)
        return result, is_error
    except Exception as exc:
        elapsed = (time.monotonic() - t0) * 1000
        err     = {"error": repr(exc)}
        record_span(name, args, err, elapsed, False)
        return err, True


# ─────────────────────────────────────────────────────────────────────────────
# 10.  Background worker thread (ticket stream consumer group + DLQ)
# ─────────────────────────────────────────────────────────────────────────────
_worker_stop   = threading.Event()
_retry_counts: dict[str, int] = defaultdict(int)
_worker_stats  = {"processed": 0, "dlq": 0}


def _process_ticket(job_id: str, issue: str, priority: str) -> bool:
    """
    Simulate ticket processing.
    Returns True on success, False on simulated transient failure.
    An issue that contains 'FAIL' is treated as repeatedly failing → DLQ.
    """
    if "FAIL" in issue.upper():
        return False
    # Simulate work
    time.sleep(0.05)
    resolution = f"Ticket {job_id} resolved by worker. Issue: {issue[:60]}"
    r.set(f"ticket:{job_id}", json.dumps({
        "status":     "resolved",
        "issue":      issue,
        "priority":   priority,
        "resolution": resolution,
    }))
    return True


def _worker_loop() -> None:
    while not _worker_stop.is_set():
        try:
            resp = r.xreadgroup(
                TICKET_GROUP, "worker-1",
                {TICKET_STREAM: ">"},
                count=5, block=200,
            )
        except Exception:
            time.sleep(0.5)
            continue

        for _stream, msgs in resp or []:
            for msg_id, fields in msgs:
                f = {k.decode(): v.decode() for k, v in fields.items()}
                job_id   = f.get("job_id", "?")
                issue    = f.get("issue", "")
                priority = f.get("priority", "normal")

                success = _process_ticket(job_id, issue, priority)

                if success:
                    r.xack(TICKET_STREAM, TICKET_GROUP, msg_id)
                    _worker_stats["processed"] += 1
                else:
                    _retry_counts[job_id] += 1
                    if _retry_counts[job_id] >= DLQ_MAX_RETRIES:
                        r.xadd(DLQ_STREAM, {
                            "job_id": job_id, "issue": issue,
                            "reason": "max_retries_exceeded",
                        })
                        r.set(f"ticket:{job_id}", json.dumps({
                            "status": "dead_letter", "issue": issue,
                            "reason": "max_retries_exceeded",
                        }))
                        r.xack(TICKET_STREAM, TICKET_GROUP, msg_id)
                        _worker_stats["dlq"] += 1


def start_worker() -> threading.Thread:
    _worker_stop.clear()
    t = threading.Thread(target=_worker_loop, daemon=True, name="ticket-worker")
    t.start()
    return t


def stop_worker() -> None:
    _worker_stop.set()


# ─────────────────────────────────────────────────────────────────────────────
# 11.  System prompt  (with prompt-caching annotation)
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent("""\
    You are a helpful customer support agent for an e-commerce store.

    ROUTING RULES — follow in order:
      1. For ANY policy or FAQ question → call recall_knowledge first.
      2. For order enquiries → call check_order_status.
      3. For refund requests → call create_refund (check order first if needed).
      4. For problems you cannot solve with the above tools → call escalate_to_human.
      5. After escalating, offer to check the ticket status with check_ticket.

    CHAINING — always chain tools when the next step depends on the previous result:
      • Refund flow:  check_order_status → create_refund
      • Escalation:  escalate_to_human → check_ticket (after a moment)

    APPROVAL GATE — if create_refund returns status='pending_approval', tell the
    customer the refund is under review and share the approval_token.

    TONE — empathetic, concise, solution-focused. Never reveal internal system details.
""")


def build_system_block() -> list[dict]:
    """
    Wrap the system prompt in a cache_control block so the Anthropic API can
    cache it across turns (saves input tokens on repeated calls).
    Only effective in LIVE mode; ignored in MOCK mode.
    """
    return [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 12.  Agent loop
# ─────────────────────────────────────────────────────────────────────────────

def agent_turn(user_text: str, session_id: str,
               verbose: bool = False) -> str:
    """
    Run one user turn through the agent:
      - loads short-term memory from Redis
      - appends the user message
      - loops until stop_reason != 'tool_use'
      - saves the final assistant message back to STM
      - prints trace table if verbose
    """

    # ── Load short-term memory ────────────────────────────────────────────────
    messages = stm_load(session_id)
    messages.append({"role": "user", "content": user_text})
    stm_append(session_id, "user", user_text)

    if not LIVE:
        # ── MOCK mode — scripted chain ────────────────────────────────────────
        return _mock_turn(user_text, session_id, verbose)

    # ── LIVE mode ─────────────────────────────────────────────────────────────
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system  = build_system_block()
    reply   = "(no reply)"

    for step in range(MAX_AGENT_STEPS):
        resp = client.messages.create(
            model      = MODEL,
            max_tokens = 1024,
            system     = system,
            tools      = TOOL_SCHEMAS,
            messages   = messages,
        )

        if verbose:
            cache_info = ""
            if hasattr(resp, "usage"):
                u = resp.usage
                cr = getattr(u, "cache_read_input_tokens",  0) or 0
                cc = getattr(u, "cache_creation_input_tokens", 0) or 0
                cache_info = f"  [tokens: in={u.input_tokens} out={u.output_tokens} cache_read={cr} cache_write={cc}]"
            print(f"  step {step+1} stop_reason={resp.stop_reason}{cache_info}")

        if resp.stop_reason == "tool_use":
            # Append assistant message
            messages.append({
                "role":    "assistant",
                "content": [b.model_dump() for b in resp.content],
            })

            # Execute every tool_use block in this response
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"    → {block.name}({json.dumps(block.input)[:80]})")
                    out, is_err = run_tool(block.name, block.input)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     json.dumps(out),
                        "is_error":    is_err,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # stop_reason == 'end_turn' (or unexpected)
        reply = "".join(b.text for b in resp.content if b.type == "text")
        break

    stm_append(session_id, "assistant", reply)
    if verbose:
        print_trace_table()
    return reply


# ─────────────────────────────────────────────────────────────────────────────
# 13.  MOCK mode — scripted multi-tool chain
# ─────────────────────────────────────────────────────────────────────────────

def _mock_turn(user_text: str, session_id: str, verbose: bool) -> str:
    """
    Exercises every tool path without a live API key.
    Mirrors the chain the agent would follow for a realistic support query.
    """
    print("  [MOCK] Scripted chain — no API key needed")

    results = {}

    # ── 1. Recall knowledge ───────────────────────────────────────────────────
    kb, _ = run_tool("recall_knowledge", {"query": "return policy refund"})
    results["kb"] = kb
    if verbose:
        print(f"  → recall_knowledge: {len(kb.get('results', []))} docs found")

    # ── 2. Check order ────────────────────────────────────────────────────────
    order, _ = run_tool("check_order_status", {"order_id": 4})
    results["order"] = order
    if verbose:
        print(f"  → check_order_status(4): status={order.get('status')}, total=${order.get('total')}")

    # ── 3a. Small refund (auto-approved) ──────────────────────────────────────
    refund_small, _ = run_tool("create_refund", {
        "order_id": 1, "amount": 129.0, "reason": "Item not as described"
    })
    results["refund_small"] = refund_small
    if verbose:
        print(f"  → create_refund(small): {refund_small.get('status')}")

    # ── 3b. Large refund (needs approval) ─────────────────────────────────────
    refund_large, _ = run_tool("create_refund", {
        "order_id": 4, "amount": 387.0, "reason": "Bulk order cancelled by customer"
    })
    results["refund_large"] = refund_large
    token = refund_large.get("approval_token", "")
    if verbose:
        print(f"  → create_refund(large): {refund_large.get('status')}, token={token}")

    # ── Simulate manager approval ─────────────────────────────────────────────
    if token:
        approved = approve(token)
        if verbose:
            print(f"  [gate] Manager approval for token {token}: {approved}")

    # ── 4. Escalate to human (async) ──────────────────────────────────────────
    esc, _ = run_tool("escalate_to_human", {
        "issue":      "Customer reports 4K monitor arrived with cracked screen.",
        "session_id": session_id,
        "priority":   "urgent",
    })
    results["escalation"] = esc
    job_id = esc.get("job_id", "")
    if verbose:
        print(f"  → escalate_to_human: job_id={job_id}")

    # Give the worker thread a moment to process
    time.sleep(0.4)

    # ── 5. Check ticket ───────────────────────────────────────────────────────
    ticket, _ = run_tool("check_ticket", {"job_id": job_id})
    results["ticket"] = ticket
    if verbose:
        print(f"  → check_ticket({job_id}): status={ticket.get('status')}")

    if verbose:
        print_trace_table()

    # ── Compose mock reply ────────────────────────────────────────────────────
    kb_snippet = (results["kb"].get("results", [{}])[0].get("text", "")[:80]
                  if results["kb"].get("results") else "N/A")
    reply = (
        f"[MOCK AGENT REPLY]\n"
        f"  KB snippet    : {kb_snippet}…\n"
        f"  Order 4 status: {order.get('status')} (${order.get('total')})\n"
        f"  Small refund  : {refund_small.get('status')}\n"
        f"  Large refund  : {refund_large.get('status')} "
        f"(approval_token={token})\n"
        f"  Escalation    : {esc.get('status')} (job_id={job_id})\n"
        f"  Ticket status : {ticket.get('status')}\n"
        f"  Worker stats  : processed={_worker_stats['processed']} "
        f"dlq={_worker_stats['dlq']}"
    )
    stm_append(session_id, "assistant", reply)
    return reply


# ─────────────────────────────────────────────────────────────────────────────
# 14.  REPL
# ─────────────────────────────────────────────────────────────────────────────

def repl(verbose: bool = False) -> None:
    session_id = uuid.uuid4().hex[:8]
    print(f"\n{'='*60}")
    print("  Support Agent  —  type 'quit' to exit, 'reset' to clear memory")
    print(f"  Mode: {'LIVE (' + MODEL + ')' if LIVE else 'MOCK (no API key)'}")
    print(f"  Session: {session_id}")
    print(f"{'='*60}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "reset":
            stm_clear(session_id)
            session_id = uuid.uuid4().hex[:8]
            print(f"  Session reset → {session_id}\n")
            continue

        reply = agent_turn(user_input, session_id, verbose=verbose)
        print(f"\nAgent: {reply}\n")


# ─────────────────────────────────────────────────────────────────────────────
# 15.  Architecture note
# ─────────────────────────────────────────────────────────────────────────────
ARCHITECTURE_NOTE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║         ARCHITECTURE NOTE — Support Agent (Day 18 Lab 2 Extension)         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  MEMORY LAYER                                                                ║
║  ┌─────────────────────────┐   ┌─────────────────────────────────────────┐  ║
║  │  Short-Term (Redis LIST) │   │  Long-Term (In-process vector store)    │  ║
║  │  • One list per session  │   │  • KB docs embedded with _embed()       │  ║
║  │  • Trimmed to MAX_HISTORY│   │  • Cosine similarity search (numpy)     │  ║
║  │  • TTL = 1 hour          │   │  • Swap _embed() for real model in prod │  ║
║  └─────────────────────────┘   └─────────────────────────────────────────┘  ║
║                                                                              ║
║  TOOL LAYER                                                                  ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │  recall_knowledge   (sync)  → vector search over KB                  │   ║
║  │  check_order_status (sync)  → parameterised SQLite read              │   ║
║  │  create_refund      (sync)  → SQLite write + approval gate           │   ║
║  │  escalate_to_human  (ASYNC) → XADD to Redis Stream, returns job_id   │   ║
║  │  check_ticket       (sync)  → poll Redis result key                  │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ASYNC QUEUE  (Redis Streams + Consumer Group)                               ║
║  Agent turn  ─XADD→  support:tickets  ─XREADGROUP→  Background worker       ║
║                                              │                               ║
║                                  success: XACK + set ticket:{id}=resolved   ║
║                                  failure: retry counter → DLQ after N tries  ║
║                                                                               ║
║  HUMAN-APPROVAL GATE                                                          ║
║  create_refund checks amount > APPROVAL_THRESHOLD ($150)                      ║
║    YES → status=pending_approval, approval_token issued, DB=pending           ║
║    NO  → status=processed immediately                                         ║
║  approve(token) / reject(token) called out-of-band (manager UI in prod)      ║
║                                                                               ║
║  OBSERVABILITY                                                                ║
║  • Trace spans: tool name, args, result summary, elapsed ms, ok/error        ║
║  • Printed as a table after each verbose turn                                 ║
║  • Worker stats: processed count + DLQ count                                 ║
║                                                                               ║
║  RESILIENCE                                                                   ║
║  • with_retry(): exponential back-off, max MAX_TOOL_RETRIES attempts         ║
║  • DLQ: tickets that fail DLQ_MAX_RETRIES times → support:tickets:dlq        ║
║                                                                               ║
║  PROMPT CACHING                                                               ║
║  • System prompt sent as {"type":"text", "cache_control":{"type":"ephemeral"}}║
║  • Anthropic API caches the prompt block across turns in the same session     ║
║  • usage.cache_read_input_tokens shows savings in verbose mode                ║
║                                                                               ║
║  ROUTING HEURISTIC (in system prompt)                                         ║
║    policy question → recall_knowledge                                         ║
║    order query     → check_order_status                                       ║
║    refund request  → check_order_status → create_refund                       ║
║    unsolvable      → escalate_to_human → check_ticket                         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────────────────────────────────────────
# 16.  Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Support agent — Day 18 Lab 2 extension"
    )
    parser.add_argument("--demo",    action="store_true",
                        help="Run one scripted demo turn and exit")
    parser.add_argument("--verbose", action="store_true",
                        help="Print tool calls, trace spans, and token usage")
    args = parser.parse_args()

    # Start background ticket worker
    worker_thread = start_worker()

    try:
        if args.demo:
            session_id = "demo-" + uuid.uuid4().hex[:6]
            print(f"\n{'='*60}")
            print("  DEMO TURN")
            print(f"  Mode: {'LIVE (' + MODEL + ')' if LIVE else 'MOCK'}")
            print(f"  Session: {session_id}")
            print(f"{'='*60}\n")

            query = (
                "Hi, I received a damaged 4K monitor in order 4. "
                "I'd like a full refund. Can you help?"
            )
            print(f"User: {query}\n")
            reply = agent_turn(query, session_id, verbose=args.verbose)
            print(f"Agent:\n{reply}\n")
            print(ARCHITECTURE_NOTE)

        else:
            repl(verbose=args.verbose)

    finally:
        stop_worker()


if __name__ == "__main__":
    main()
