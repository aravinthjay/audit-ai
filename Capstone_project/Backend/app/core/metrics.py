"""
Prometheus metrics registry for the Skeptic Engine backend.

Exposed at GET /metrics (wired in app/main.py via prometheus-fastapi-instrumentator,
which also emits the standard http_request_* series automatically). Everything in
this module is the app-specific, business-level telemetry: LLM call cost/latency/
tokens, investigation pipeline outcomes, debate rounds, and verification results.
"""

from prometheus_client import Counter, Histogram

# --- LLM call telemetry (one _record_call in app/llm/service.py feeds all of these) ---

llm_calls_total = Counter(
    "skeptic_llm_calls_total",
    "Total LLM provider calls",
    ["provider", "model", "request_type", "success", "cache_hit", "fallback_used"],
)

llm_call_latency_seconds = Histogram(
    "skeptic_llm_call_latency_seconds",
    "LLM provider call latency",
    ["provider", "model", "request_type"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 45, 90),
)

llm_tokens_total = Counter(
    "skeptic_llm_tokens_total",
    "Total tokens consumed by LLM calls",
    ["provider", "model", "token_type"],  # token_type: prompt | completion
)

llm_cost_usd_total = Counter(
    "skeptic_llm_cost_usd_total",
    "Estimated USD cost of LLM calls",
    ["provider", "model", "request_type"],
)

# --- Investigation pipeline telemetry (app/agents/executor.py) ---

investigations_total = Counter(
    "skeptic_investigations_total",
    "Investigations processed by terminal outcome",
    ["status"],  # completed | review | escalated | failed
)

investigation_duration_seconds = Histogram(
    "skeptic_investigation_duration_seconds",
    "Wall-clock duration of a full investigation run",
    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1200),
)

investigation_phase_duration_seconds = Histogram(
    "skeptic_investigation_phase_duration_seconds",
    "Wall-clock duration of a single investigation phase",
    ["phase"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)

debate_rounds_total = Counter(
    "skeptic_debate_rounds_total",
    "Challenger/Defender debate rounds executed",
)

verification_results_total = Counter(
    "skeptic_verification_results_total",
    "Verifier outcomes per investigation attempt",
    ["grounded"],  # true | false
)
