"""
Day 18 Colab 1 — Extension Tasks 1 to 5
=========================================
Extension 1: Rolling summary / compaction
Extension 2: TTL & forget_fact tool
Extension 3: Parallel lookups (get_customer + get_order in one turn)
Extension 4: Guarded writes / PII rejection
Extension 5: Token accounting (cumulative input/output tokens)
"""

import os
import re
import json
import time
import getpass
import fakeredis
from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Setup — API key
# ---------------------------------------------------------------------------
if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter your Anthropic API key: ")

MODEL       = "claude-sonnet-4-6"
CHEAP_MODEL = "claude-haiku-4-5-20251001"   # used for cheap summarisation in Ext 1
clientA     = Anthropic()


# ---------------------------------------------------------------------------
# FastAPI backend — extended with /customers/{id} for Extension 3
# ---------------------------------------------------------------------------
app = FastAPI()

_ORDERS = {
    "A1001": {"id": "A1001", "item": "Mechanical keyboard", "qty": 1, "status": "shipped",    "total": 129.0},
    "A1002": {"id": "A1002", "item": "USB-C hub",           "qty": 2, "status": "processing", "total": 58.0},
    "A1003": {"id": "A1003", "item": "4K monitor",          "qty": 1, "status": "delivered",  "total": 410.0},
}

# Extension 3 — second endpoint
_CUSTOMERS = {
    "C001": {"id": "C001", "name": "Asha Patel",   "email": "asha@example.com",  "tier": "gold"},
    "C002": {"id": "C002", "name": "Ravi Sharma",  "email": "ravi@example.com",  "tier": "silver"},
    "C003": {"id": "C003", "name": "Priya Menon",  "email": "priya@example.com", "tier": "bronze"},
}

@app.get("/orders/{order_id}")
def get_order_endpoint(order_id: str):
    o = _ORDERS.get(order_id.upper())
    if not o:
        raise HTTPException(status_code=404, detail="order not found")
    return o

@app.get("/customers/{customer_id}")
def get_customer_endpoint(customer_id: str):
    c = _CUSTOMERS.get(customer_id.upper())
    if not c:
        raise HTTPException(status_code=404, detail="customer not found")
    return c

http_client = TestClient(app)
print("FastAPI test client ready.")


# ---------------------------------------------------------------------------
# Extension 1 — RedisMemory with rolling summary / compaction
# ---------------------------------------------------------------------------
#
# How it works:
#   When load_history() would exceed COMPACTION_THRESHOLD turns, the oldest
#   half of the conversation is sent to a cheap Claude model (claude-haiku)
#   which summarises them into a single synthetic assistant message.
#   That summary replaces the old turns, keeping total context bounded.
#
#   Example:
#     Before:  [turn1, turn2, turn3, turn4, turn5, turn6, turn7, turn8]
#     After:   [SUMMARY of turns1-4, turn5, turn6, turn7, turn8]
#
# ---------------------------------------------------------------------------

class RedisMemory:
    def __init__(self, r, session_id: str,
                 history_limit: int = 40,
                 compaction_threshold: int = 10):
        self.r = r
        self.sid = session_id
        self.history_limit = history_limit
        self.compaction_threshold = compaction_threshold   # Ext 1
        self.h_key = f"hist:{session_id}"
        self.f_key = f"facts:{session_id}"

    # ── short-term: conversation turns ────────────────────────────────────
    def append_turn(self, role: str, content):
        self.r.rpush(self.h_key, json.dumps({"role": role, "content": content}))
        self.r.ltrim(self.h_key, -self.history_limit, -1)

    def load_history(self):
        turns = [json.loads(x) for x in self.r.lrange(self.h_key, 0, -1)]
        # Extension 1: compact if over threshold
        if len(turns) > self.compaction_threshold:
            turns = self._compact(turns)
        return turns

    # Extension 1 — compaction logic
    def _compact(self, turns: list) -> list:
        """
        Summarise the oldest half of turns with a cheap model call.
        Replace those turns with one synthetic assistant summary message.
        """
        half      = len(turns) // 2
        old_turns = turns[:half]
        new_turns = turns[half:]

        # Build a prompt asking for a compact summary
        history_text = "\n".join(
            f"{t['role'].upper()}: "
            f"{t['content'] if isinstance(t['content'], str) else json.dumps(t['content'])}"
            for t in old_turns
        )
        summary_resp = clientA.messages.create(
            model=CHEAP_MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    "Summarise this conversation excerpt in 2-3 sentences. "
                    "Preserve key facts (order IDs, preferences, names).\n\n"
                    f"{history_text}"
                )
            }]
        )
        summary_text = summary_resp.content[0].text
        summary_msg  = {
            "role": "assistant",
            "content": f"[Conversation summary] {summary_text}"
        }

        # Rewrite Redis list: summary + recent turns
        compacted = [summary_msg] + new_turns
        self.r.delete(self.h_key)
        for turn in compacted:
            self.r.rpush(self.h_key, json.dumps(turn))

        print(f"  [Ext 1] Compacted {half} old turns into 1 summary message. "
              f"History now {len(compacted)} turns.")
        return compacted

    # ── long-term: durable facts ───────────────────────────────────────────
    def set_fact(self, key: str, value: str, ttl_seconds: int | None = None):
        # Extension 2 — per-key TTL using a shadow expiry key
        self.r.hset(self.f_key, key, value)
        if ttl_seconds:
            expiry_at = time.time() + ttl_seconds
            self.r.hset(f"{self.f_key}:ttl", key, expiry_at)
            print(f"  [Ext 2] Fact '{key}' will expire in {ttl_seconds}s "
                  f"(at {expiry_at:.0f})")

    def get_fact(self, key: str):
        # Extension 2 — check per-key TTL before returning
        ttl_val = self.r.hget(f"{self.f_key}:ttl", key)
        if ttl_val:
            expiry_at = float(ttl_val.decode() if isinstance(ttl_val, bytes) else ttl_val)
            if time.time() > expiry_at:
                # Expired — delete and return None
                self.r.hdel(self.f_key, key)
                self.r.hdel(f"{self.f_key}:ttl", key)
                print(f"  [Ext 2] Fact '{key}' has expired — returning None.")
                return None
        v = self.r.hget(self.f_key, key)
        return v.decode() if isinstance(v, bytes) else v

    def forget_fact(self, key: str):
        # Extension 2 — explicit delete
        deleted = self.r.hdel(self.f_key, key)
        self.r.hdel(f"{self.f_key}:ttl", key)
        return deleted > 0

    def all_facts(self):
        raw = self.r.hgetall(self.f_key)
        return {k.decode(): v.decode() for k, v in raw.items()}


# Initialise shared memory
r   = fakeredis.FakeStrictRedis()
mem = RedisMemory(r, session_id="demo-user", compaction_threshold=10)


# ---------------------------------------------------------------------------
# Extension 4 — PII guard helpers
# ---------------------------------------------------------------------------
#
# How it works:
#   Before storing any fact, run two regex checks:
#     1. Card number pattern — 13-19 digits, optionally separated by spaces/dashes
#     2. Email pattern — standard email format
#   If either matches, return is_error=True with a helpful message.
#   The agent receives the error and recovers gracefully (tells the user it
#   can't store that information).
#
# ---------------------------------------------------------------------------

_CARD_RE  = re.compile(r'\b(?:\d[ -]?){13,19}\b')
_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')

def _contains_pii(value: str) -> str | None:
    """Return a description of the PII found, or None if clean."""
    if _CARD_RE.search(value):
        return "a card number"
    if _EMAIL_RE.search(value):
        return "an email address"
    return None


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def tool_get_order(order_id: str) -> dict:
    resp = http_client.get(f"/orders/{order_id}")
    if resp.status_code == 404:
        return {"error": f"No order {order_id} found."}
    resp.raise_for_status()
    return resp.json()


# Extension 3 — get_customer tool
def tool_get_customer(customer_id: str) -> dict:
    resp = http_client.get(f"/customers/{customer_id}")
    if resp.status_code == 404:
        return {"error": f"No customer {customer_id} found."}
    resp.raise_for_status()
    return resp.json()


# Extension 4 — PII-guarded remember
def tool_remember_fact(key: str, value: str) -> dict:
    pii_type = _contains_pii(value)
    if pii_type:
        msg = (f"Cannot store this value — it appears to contain {pii_type}. "
               "For security reasons, PII cannot be saved in user facts. "
               "Please provide a non-sensitive value instead.")
        print(f"  [Ext 4] PII rejected: {pii_type} detected in value for key '{key}'")
        return {"error": msg}
    mem.set_fact(key, value)
    return {"ok": True, "stored": {key: value}}


def tool_recall_fact(key: str) -> dict:
    v = mem.get_fact(key)
    return {"key": key, "value": v} if v is not None else {"key": key, "value": None}


# Extension 2 — forget_fact tool
def tool_forget_fact(key: str) -> dict:
    deleted = mem.forget_fact(key)
    return {"ok": True, "deleted": key} if deleted else {"ok": False, "message": f"No fact '{key}' found."}


# ---------------------------------------------------------------------------
# Tool schemas — all five tools
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_order",
        "description": "Look up a customer order by its ID. Returns item, quantity, status and total.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID like 'A1001'.",
                    "pattern": "^[Aa][0-9]{4}$"
                }
            },
            "required": ["order_id"],
        },
    },
    # Extension 3 — second tool
    {
        "name": "get_customer",
        "description": "Look up a customer profile by their customer ID. Returns name, email, and tier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID like 'C001'.",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "remember_fact",
        "description": (
            "Persist a durable fact about the user for future turns. "
            "Do NOT store sensitive data like card numbers or email addresses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key":   {"type": "string", "description": "Short fact key, e.g. 'shipping_pref'."},
                "value": {"type": "string", "description": "The fact value to store."},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "recall_fact",
        "description": "Retrieve a previously stored fact about the user by key. Returns null if unknown or expired.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The fact key to look up."}
            },
            "required": ["key"],
        },
    },
    # Extension 2 — forget tool
    {
        "name": "forget_fact",
        "description": "Delete a stored fact about the user by key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The fact key to delete."}
            },
            "required": ["key"],
        },
    },
]

DISPATCH = {
    "get_order":     tool_get_order,
    "get_customer":  tool_get_customer,       # Extension 3
    "remember_fact": tool_remember_fact,      # Extension 4 (PII guard inside)
    "recall_fact":   tool_recall_fact,
    "forget_fact":   tool_forget_fact,        # Extension 2
}


def run_tool(name: str, args: dict) -> tuple[dict, bool]:
    fn = DISPATCH.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}, True
    try:
        out    = fn(**args)
        is_err = isinstance(out, dict) and "error" in out
        return out, is_err
    except Exception as e:
        return {"error": repr(e)}, True


# ---------------------------------------------------------------------------
# Extension 5 — Token accounting
# ---------------------------------------------------------------------------
#
# How it works:
#   resp.usage returns an object with:
#     input_tokens  — tokens the model read this call
#     output_tokens — tokens the model generated this call
#   We accumulate these across every step in a turn (there can be multiple
#   API calls per turn if the model uses tools) and print the totals.
#
# ---------------------------------------------------------------------------

class TokenAccumulator:
    def __init__(self):
        self.total_input  = 0
        self.total_output = 0

    def add(self, usage):
        self.total_input  += usage.input_tokens
        self.total_output += usage.output_tokens

    def report(self, label: str = ""):
        print(f"  [Ext 5] Tokens{' (' + label + ')' if label else ''} — "
              f"input: {self.total_input}  output: {self.total_output}  "
              f"total: {self.total_input + self.total_output}")


# ---------------------------------------------------------------------------
# Agent loop — all extensions wired in
# ---------------------------------------------------------------------------

SYSTEM = (
    "You are an order-support assistant. "
    "Use get_order for order questions, get_customer for customer profile questions. "
    "Use remember_fact / recall_fact / forget_fact for durable user preferences. "
    "Do NOT store sensitive data like emails or card numbers. "
    "Be concise."
)


def agent_turn(user_text: str, max_steps: int = 8, verbose: bool = True) -> str:
    mem.append_turn("user", user_text)
    messages = mem.load_history()

    # Extension 5 — token accumulator for this turn
    tokens = TokenAccumulator()

    for step in range(max_steps):
        resp = clientA.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        # Extension 5 — accumulate tokens each API call
        tokens.add(resp.usage)

        if resp.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": [b.model_dump() for b in resp.content]
            })
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"  → tool call: {block.name}({block.input})")
                    out, is_err = run_tool(block.name, block.input)
                    if verbose:
                        print(f"    ← result: {out}")
                    results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     json.dumps(out),
                        "is_error":    is_err,
                    })
            messages.append({"role": "user", "content": results})
            continue

        # end_turn
        text = "".join(b.text for b in resp.content if b.type == "text")
        mem.append_turn("assistant", text)

        # Extension 5 — print token summary for this full turn
        if verbose:
            tokens.report(label=f"turn step {step + 1}")

        return text

    return "(stopped: max steps reached)"


# ---------------------------------------------------------------------------
# Demo — one section per extension
# ---------------------------------------------------------------------------

def separator(title: str):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run_extension_1():
    separator("EXTENSION 1 — Rolling Summary / Compaction")
    print("Filling history with 12 turns to trigger compaction...\n")

    # Force 12 turns into history to exceed compaction_threshold of 10
    for i in range(1, 7):
        mem.append_turn("user",      f"This is user message {i}.")
        mem.append_turn("assistant", f"This is assistant reply {i}.")

    print(f"History length before load_history(): {len(mem.r.lrange(mem.h_key, 0, -1))} turns")
    history = mem.load_history()   # compaction triggers here
    print(f"History length after  load_history(): {len(history)} turns")
    print(f"First entry after compaction:\n  {history[0]['content'][:120]}...")


def run_extension_2():
    separator("EXTENSION 2 — TTL & forget_fact Tool")

    print("Storing a fact with a 2-second TTL...")
    mem.set_fact("promo_code", "SAVE20", ttl_seconds=2)
    print(f"  Immediately: {mem.get_fact('promo_code')}")

    print("Waiting 3 seconds for TTL to expire...")
    time.sleep(3)
    print(f"  After expiry: {mem.get_fact('promo_code')}")

    print("\nStoring a permanent fact, then explicitly forgetting it...")
    mem.set_fact("shipping_pref", "express")
    print(f"  Before forget: {mem.get_fact('shipping_pref')}")
    result = tool_forget_fact("shipping_pref")
    print(f"  forget_fact result: {result}")
    print(f"  After forget: {mem.get_fact('shipping_pref')}")

    print("\nAsking agent to forget a fact via natural language...")
    reply = agent_turn("Please forget my shipping preference if you have it stored.", verbose=True)
    print(f"Agent: {reply}")


def run_extension_3():
    separator("EXTENSION 3 — Parallel Lookups (two tool_use blocks in one turn)")
    print("Asking a question that requires BOTH get_order AND get_customer...\n")
    print("Watch for two tool calls emitted in the same turn:\n")

    reply = agent_turn(
        "Can you look up order A1001 and also pull up customer profile C001 at the same time?",
        verbose=True
    )
    print(f"\nAgent: {reply}")


def run_extension_4():
    separator("EXTENSION 4 — Guarded Writes / PII Rejection")

    print("Test 1: Trying to store an email address directly...\n")
    result, is_err = run_tool("remember_fact", {"key": "contact", "value": "asha@example.com"})
    print(f"  Result: {result}")
    print(f"  is_error: {is_err}")

    print("\nTest 2: Trying to store a card number directly...\n")
    result, is_err = run_tool("remember_fact", {"key": "payment", "value": "4111 1111 1111 1111"})
    print(f"  Result: {result}")
    print(f"  is_error: {is_err}")

    print("\nTest 3: Agent tries to store an email — confirm it recovers gracefully...\n")
    reply = agent_turn(
        "Please remember my email address as user@example.com for future reference.",
        verbose=True
    )
    print(f"\nAgent: {reply}")

    print("\nTest 4: Storing a clean value works fine...\n")
    result, is_err = run_tool("remember_fact", {"key": "shipping_pref", "value": "express"})
    print(f"  Result: {result}")
    print(f"  is_error: {is_err}")


def run_extension_5():
    separator("EXTENSION 5 — Token Accounting")
    print("Each API call's token usage is printed after the turn completes.\n")

    reply = agent_turn(
        "What is the status of order A1002 and what is its total price?",
        verbose=True
    )
    print(f"\nAgent: {reply}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_extension_1()
    run_extension_2()
    run_extension_3()
    run_extension_4()
    run_extension_5()

    print()
    print("=" * 60)
    print("  All 5 extension tasks complete.")
    print("=" * 60)
