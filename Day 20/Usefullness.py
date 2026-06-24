"""
usefulness_groundedness.py
==========================
Standalone module for evaluating LLM outputs on two axes:

  1. GROUNDEDNESS  – is the summary faithful to the source material?
               Two layers:
               a) Heuristic guardrail  (fast, zero-cost, token-overlap)
               b) LLM-as-judge         (precise, uses MODEL_JUDGEMENT)

  2. USEFULNESS   – does the output actually help a downstream consumer?
               Two layers:
               a) Heuristic guardrail  (fast, checks length / vagueness)
               b) LLM-as-judge         (precise, uses MODEL_JUDGEMENT)

Run the file directly to see all checks applied to three example outputs.
"""

import os, re, json, time, random
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# 0 · Config & model wrapper
# ---------------------------------------------------------------------------
MODEL_JUDGEMENT = "claude-sonnet-4-6"
MODEL_ROUTINE   = "claude-haiku-4-5-20251001"
USE_MOCK        = not bool(os.environ.get("ANTHROPIC_API_KEY"))

PRICES = {
    MODEL_ROUTINE:   {"in": 1.00, "out": 5.00},
    MODEL_JUDGEMENT: {"in": 3.00, "out": 15.00},
}

@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    mock: bool

def _estimate_tokens(s: str) -> int:
    return max(1, len(s) // 4)

def _mock_judge_response() -> str:
    return json.dumps({
        "groundedness": random.randint(2, 5),
        "usefulness":   random.randint(2, 5),
        "groundedness_reason": "Mock: summary stays close to source facts.",
        "usefulness_reason":   "Mock: gives a sales rep a clear next action.",
    })

def call_claude(prompt: str,
                model: str = MODEL_ROUTINE,
                system: str = "",
                max_tokens: int = 400) -> LLMResult:
    t0 = time.perf_counter()
    if USE_MOCK:
        text = _mock_judge_response()
        it, ot = _estimate_tokens(system + prompt), _estimate_tokens(text)
        mock = True
    else:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=model, max_tokens=max_tokens,
            system=system or "You are a precise evaluator. Return only valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        it, ot = msg.usage.input_tokens, msg.usage.output_tokens
        mock = False
    dt  = (time.perf_counter() - t0) * 1000
    p   = PRICES.get(model, {"in": 0, "out": 0})
    cost = it / 1e6 * p["in"] + ot / 1e6 * p["out"]
    return LLMResult(text, model, it, ot, round(dt, 1), round(cost, 6), mock)


# ---------------------------------------------------------------------------
# 1 · GuardResult dataclass (shared by both guardrails)
# ---------------------------------------------------------------------------
@dataclass
class GuardResult:
    """
    allowed   – True = output passes this check
    rule      – machine-readable rule name
    reason    – human-readable explanation (empty when passing)
    severity  – 'low' | 'medium' | 'high'
    score     – optional 0-1 continuous score (1 = best)
    """
    allowed:  bool
    rule:     str
    reason:   str = ""
    severity: str = "medium"
    score:    Optional[float] = None

    def __repr__(self):
        status = "PASS" if self.allowed else "FAIL"
        score_str = f"  score={self.score:.2f}" if self.score is not None else ""
        return f"[{status}] {self.rule}{score_str}  {self.reason}"


# ---------------------------------------------------------------------------
# 2 · Groundedness
# ---------------------------------------------------------------------------

# ---- 2a. Heuristic guardrail (token overlap) ----

def gr_grounded(summary: str, source: str, threshold: float = 0.15) -> GuardResult:
    """
    Fast, zero-cost grounding check.

    Strategy: extract all words ≥4 chars from both texts, measure the
    fraction of summary words that also appear in the source.  A low
    overlap means the summary is likely hallucinating or paraphrasing
    facts not present in the source.

    threshold – fraction of summary tokens that must appear in source
                (default 0.15, i.e. 15 %).  Tune upward for stricter checks.
    """
    summary_tokens = set(re.findall(r"[a-z]{4,}", (summary or "").lower()))
    source_tokens  = set(re.findall(r"[a-z]{4,}", (source  or "").lower()))

    if not summary_tokens:
        return GuardResult(True, "grounded", "empty summary – trivially grounded", score=1.0)

    overlap = len(summary_tokens & source_tokens) / len(summary_tokens)
    score   = round(overlap, 3)

    if overlap >= threshold:
        return GuardResult(True,  "grounded", f"overlap={overlap:.2f} ≥ {threshold}", score=score)
    else:
        return GuardResult(False, "grounded",
                           f"low overlap={overlap:.2f} < {threshold} – possible hallucination",
                           severity="medium", score=score)


# ---- 2b. LLM-as-judge groundedness ----

GROUNDEDNESS_SYSTEM = """\
You are a strict fact-checker.  Given a SOURCE text and a SUMMARY, decide whether
every factual claim in the SUMMARY is directly supported by the SOURCE.

Return ONLY a JSON object with these keys (no markdown, no prose):
  "groundedness": integer 1-5
      5 = every claim is explicitly in the source
      4 = minor inference but nothing contradicted
      3 = some unsupported claims
      2 = most claims are unsupported or distorted
      1 = the summary contradicts the source
  "groundedness_reason": one-sentence explanation
"""

def judge_groundedness(summary: str, source: str) -> dict:
    """
    Ask an LLM to rate how well the summary is grounded in the source.
    Returns {"groundedness": int, "groundedness_reason": str, "cost_usd": float}.
    """
    prompt = f"SOURCE:\n{source}\n\nSUMMARY:\n{summary}"
    res    = call_claude(prompt, model=MODEL_JUDGEMENT, system=GROUNDEDNESS_SYSTEM, max_tokens=150)
    try:
        data = json.loads(res.text)
    except Exception:
        data = {"groundedness": 3, "groundedness_reason": "unparseable; defaulted to 3"}
    data["cost_usd"] = res.cost_usd
    return data


# ---------------------------------------------------------------------------
# 3 · Usefulness
# ---------------------------------------------------------------------------

# ---- 3a. Heuristic guardrail ----

VAGUE_PHRASES = [
    "mock response", "acknowledged", "n/a", "not applicable",
    "i don't know", "no information", "lorem ipsum",
]
MIN_USEFUL_LENGTH = 30   # characters; below this a summary is almost certainly useless

def gr_useful(text: str) -> GuardResult:
    """
    Fast, zero-cost usefulness check.

    Flags outputs that are:
      • Too short to carry any real information
      • Filled with known filler / placeholder phrases
      • Pure repetition of the input prompt (naïve echo)

    This does NOT replace the LLM judge; it catches obvious failures cheaply.
    """
    t = (text or "").strip()

    if len(t) < MIN_USEFUL_LENGTH:
        return GuardResult(False, "useful",
                           f"too short ({len(t)} chars < {MIN_USEFUL_LENGTH})",
                           severity="high", score=0.0)

    low = t.lower()
    for phrase in VAGUE_PHRASES:
        if phrase in low:
            return GuardResult(False, "useful",
                               f"contains vague/filler phrase: '{phrase}'",
                               severity="medium", score=0.1)

    # Rough uniqueness: if >70 % of words are repeated from a 5-word window it's likely a loop
    words = low.split()
    if len(words) >= 10:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.35:
            return GuardResult(False, "useful",
                               f"low lexical diversity ({unique_ratio:.2f}) – possible loop/echo",
                               severity="medium", score=round(unique_ratio, 2))

    score = min(1.0, len(t) / 300)   # naive length-based proxy, capped at 1
    return GuardResult(True, "useful", f"passed heuristic checks", score=round(score, 2))


# ---- 3b. LLM-as-judge usefulness ----

USEFULNESS_SYSTEM = """\
You are evaluating whether a lead summary is useful to a B2B sales representative.

A useful summary:
  • Names the company's specific pain point
  • Gives at least one concrete, actionable next step or conversation hook
  • Is concise (< 100 words) and avoids generic filler

Return ONLY a JSON object with these keys (no markdown, no prose):
  "usefulness": integer 1-5
      5 = immediately actionable; sales rep knows exactly what to say
      4 = good context; minor gaps
      3 = some useful info but too vague for direct action
      2 = mostly generic; hard to act on
      1 = useless or misleading
  "usefulness_reason": one-sentence explanation
"""

def judge_usefulness(summary: str, context: str = "") -> dict:
    """
    Ask an LLM to rate how useful the summary is for a downstream sales rep.
    context – optional background (industry, company size) to ground the rating.
    Returns {"usefulness": int, "usefulness_reason": str, "cost_usd": float}.
    """
    ctx_block = f"\nCONTEXT:\n{context}" if context else ""
    prompt    = f"SUMMARY:\n{summary}{ctx_block}"
    res       = call_claude(prompt, model=MODEL_JUDGEMENT, system=USEFULNESS_SYSTEM, max_tokens=150)
    try:
        data = json.loads(res.text)
    except Exception:
        data = {"usefulness": 3, "usefulness_reason": "unparseable; defaulted to 3"}
    data["cost_usd"] = res.cost_usd
    return data


# ---------------------------------------------------------------------------
# 4 · Combined judge (groundedness + usefulness in one call – saves tokens)
# ---------------------------------------------------------------------------

COMBINED_JUDGE_SYSTEM = """\
You are a quality evaluator for a B2B sales pipeline.

Given a SOURCE text and a SUMMARY, rate the summary on two dimensions.

Return ONLY a JSON object with these keys (no markdown fences, no extra text):
  "groundedness": integer 1-5
      5 = every claim explicitly supported by the source
      3 = some unsupported claims
      1 = contradicts the source
  "groundedness_reason": one sentence

  "usefulness": integer 1-5
      5 = immediately actionable for a sales rep
      3 = some useful info but vague
      1 = useless or misleading
  "usefulness_reason": one sentence
"""

def judge_combined(summary: str, source: str) -> dict:
    """
    Single LLM call that scores both groundedness AND usefulness.
    More token-efficient than two separate calls.
    Returns the parsed dict plus cost_usd.
    """
    prompt = f"SOURCE:\n{source}\n\nSUMMARY:\n{summary}"
    res    = call_claude(prompt, model=MODEL_JUDGEMENT, system=COMBINED_JUDGE_SYSTEM, max_tokens=200)
    try:
        data = json.loads(res.text)
    except Exception:
        data = {
            "groundedness": 3, "groundedness_reason": "unparseable; defaulted",
            "usefulness":   3, "usefulness_reason":   "unparseable; defaulted",
        }
    data["cost_usd"] = res.cost_usd
    return data


# ---------------------------------------------------------------------------
# 5 · Aggregate scores across many evaluations
# ---------------------------------------------------------------------------

def aggregate_scores(scores: list[dict]) -> dict:
    """
    Average groundedness and usefulness across a batch of judge results.
    Also counts how many outputs fall below a quality threshold (score < 3).
    """
    if not scores:
        return {}
    keys = ("groundedness", "usefulness")
    avg  = {k: round(sum(s.get(k, 0) for s in scores) / len(scores), 2) for k in keys}
    avg["n"]                    = len(scores)
    avg["low_groundedness"]     = sum(1 for s in scores if s.get("groundedness", 5) < 3)
    avg["low_usefulness"]       = sum(1 for s in scores if s.get("usefulness",   5) < 3)
    return avg


# ---------------------------------------------------------------------------
# 6 · Full evaluation pipeline for one output
# ---------------------------------------------------------------------------

def evaluate_output(summary: str,
                    source:  str,
                    context: str = "",
                    use_llm: bool = True) -> dict:
    """
    Run all four checks on a single (summary, source) pair.

    Returns a dict with:
      heuristic_grounded  – GuardResult
      heuristic_useful    – GuardResult
      llm_scores          – dict from judge_combined (only if use_llm=True)
      overall_pass        – True if both heuristics pass AND llm scores ≥ 3
    """
    h_grounded = gr_grounded(summary, source)
    h_useful   = gr_useful(summary)

    result = {
        "heuristic_grounded": h_grounded,
        "heuristic_useful":   h_useful,
        "llm_scores":         None,
        "overall_pass":       h_grounded.allowed and h_useful.allowed,
    }

    if use_llm:
        llm = judge_combined(summary, source)
        result["llm_scores"]  = llm
        result["overall_pass"] = (
            h_grounded.allowed
            and h_useful.allowed
            and llm.get("groundedness", 0) >= 3
            and llm.get("usefulness",   0) >= 3
        )

    return result


# ---------------------------------------------------------------------------
# 7 · Demo / smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 58)
    print(" USEFULNESS & GROUNDEDNESS EVALUATION — DEMO")
    print(f" mode: {'MOCK' if USE_MOCK else 'LIVE API'}")
    print("=" * 58)

    # Three test cases: good, hallucinated, useless
    cases = [
        {
            "label":   "Good summary",
            "source":  ("Northwind Logistics (320 employees) is exploring warehouse "
                        "automation to cut manual data entry. Contact: ops@northwind.example"),
            "summary": ("Northwind Logistics, a 320-person logistics firm, wants to automate "
                        "their warehouse to reduce manual data-entry overhead. Strong ICP fit; "
                        "recommend a demo focused on the data-capture module."),
        },
        {
            "label":   "Hallucinated summary",
            "source":  ("Acme Tiny Bakery (4 employees, local shop, no budget mentioned.)"),
            "summary": ("Acme Bakery is a Series-B funded cloud-kitchen startup with $10M ARR "
                        "expanding internationally. Immediate upsell opportunity."),
        },
        {
            "label":   "Useless / vague summary",
            "source":  ("Helios FinServ (1500 employees) wants AI for back-office processes."),
            "summary": ("Mock response: acknowledged."),
        },
    ]

    all_llm_scores = []

    for case in cases:
        print(f"\n{'─'*58}")
        print(f"  Case : {case['label']}")
        print(f"  Source  : {case['source'][:70]}…" if len(case['source']) > 70 else f"  Source  : {case['source']}")
        print(f"  Summary : {case['summary'][:70]}…" if len(case['summary']) > 70 else f"  Summary : {case['summary']}")
        print()

        ev = evaluate_output(case["summary"], case["source"])

        print(f"  Heuristic groundedness : {ev['heuristic_grounded']}")
        print(f"  Heuristic usefulness   : {ev['heuristic_useful']}")

        if ev["llm_scores"]:
            llm = ev["llm_scores"]
            print(f"  LLM groundedness       : {llm.get('groundedness')}/5  — {llm.get('groundedness_reason','')}")
            print(f"  LLM usefulness         : {llm.get('usefulness')}/5  — {llm.get('usefulness_reason','')}")
            print(f"  Cost (this call)       : ${llm.get('cost_usd', 0):.6f}")
            all_llm_scores.append(llm)

        print(f"  ► OVERALL PASS         : {ev['overall_pass']}")

    if all_llm_scores:
        agg = aggregate_scores(all_llm_scores)
        print(f"\n{'='*58}")
        print(f" AGGREGATE ({agg['n']} outputs)")
        print(f"  avg groundedness : {agg['groundedness']}")
        print(f"  avg usefulness   : {agg['usefulness']}")
        print(f"  low groundedness : {agg['low_groundedness']}")
        print(f"  low usefulness   : {agg['low_usefulness']}")
        print("=" * 58)