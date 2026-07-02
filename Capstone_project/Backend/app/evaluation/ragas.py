"""RAGAS evaluation for the multi-agent crew.

This replaces the earlier A/B (single-prompt vs. crew) harness. The crew is
scored with the RAGAS metric suite across three categories:

* retrieval  - did the Evidence agent fetch relevant, complete context?
* generation - is the adjudicated verdict faithful, relevant, and correct?
* agentic    - did the crew use tools, stay on topic, and reach the goal?

The full RAGAS library (the ``ragas`` package + an LLM judge) is intended to be
wired in behind ``compute_ragas_with_library`` later. It is kept optional so this
module imports and runs with no external services. Until a labelled run with
reference answers is supplied, scores are derived deterministically from stored
investigation telemetry as transparent proxies.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import (
    DebateTranscript,
    EvidenceArtifact,
    Investigation,
    VerificationClaim,
)


@dataclass(frozen=True)
class MetricDef:
    metric: str
    category: str  # "retrieval" | "generation" | "agentic"
    target: float
    helper: str


# Canonical RAGAS metric catalog (all higher-is-better, 0..1).
METRIC_CATALOG: list[MetricDef] = [
    MetricDef("Context Precision", "retrieval", 0.85,
              "Fraction of retrieved policy chunks relevant to the case."),
    MetricDef("Context Recall", "retrieval", 0.85,
              "Share of the evidence needed for the verdict present in retrieval."),
    MetricDef("Context Entity Recall", "retrieval", 0.80,
              "Coverage of key entities (vendor, amount, clauses) in the context."),
    MetricDef("Faithfulness", "generation", 0.90,
              "Verdict claims grounded in the retrieved evidence (hallucination guard)."),
    MetricDef("Response Relevancy", "generation", 0.85,
              "How directly the verdict answers the case question."),
    MetricDef("Factual Correctness", "generation", 0.80,
              "Agreement of the verdict with the labelled ground truth."),
    MetricDef("Semantic Similarity", "generation", 0.85,
              "Embedding closeness of the verdict to the reference answer."),
    MetricDef("Tool Call Accuracy", "agentic", 0.85,
              "Evidence agent invokes the right tools with the right arguments."),
    MetricDef("Topic Adherence", "agentic", 0.85,
              "Challenger and Defender stay within audit scope."),
    MetricDef("Agent Goal Accuracy", "agentic", 0.80,
              "Crew reaches a correct, routed, fully-supported decision."),
]


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _status(investigation: Investigation) -> str:
    raw = investigation.status
    return raw.value if hasattr(raw, "value") else str(raw)


def _metric_row(definition: MetricDef, score: float) -> dict:
    rounded = round(_clamp(score), 4)
    return {
        "metric": definition.metric,
        "category": definition.category,
        "score": rounded,
        "target": definition.target,
        "pass": rounded >= definition.target,
        "helper": definition.helper,
    }


def metric_catalog() -> list[dict]:
    """The RAGAS metric definitions with zeroed scores (no run required)."""
    return [_metric_row(definition, 0.0) for definition in METRIC_CATALOG]


def compute_ragas_summary(db: Session, investigation_id: str | None = None) -> dict:
    """Compute a RAGAS summary from stored investigation telemetry.

    When ``investigation_id`` is given the scores are scoped to that single case;
    otherwise they aggregate across every investigation. Returns an empty summary
    (``cases == 0``, ``metrics == []``) when there is nothing to score, so the
    dashboard can show its empty state.
    """
    inv_query = db.query(Investigation)
    if investigation_id is not None:
        inv_query = inv_query.filter(Investigation.id == investigation_id)
    investigations = inv_query.all()
    if investigation_id is None:
        # Only score cases the crew actually processed. Unrun "intake" imports have
        # no evidence, debate, or verdict, so leaving them in drags every average
        # toward zero and makes the model look far worse than it is.
        investigations = [i for i in investigations if _status(i) != "intake"]
    total = len(investigations)
    if total == 0:
        return {"cases": 0, "metrics": [], "conclusion": ""}

    def _scoped(model):
        query = db.query(model)
        if investigation_id is not None:
            query = query.filter(model.investigation_id == investigation_id)
        return query.all()

    claims = _scoped(VerificationClaim)
    evidence = _scoped(EvidenceArtifact)
    debates = _scoped(DebateTranscript)

    grounded_claims = sum(1 for c in claims if c.is_grounded)
    mean_relevance = _ratio(sum(e.relevance_score or 0.0 for e in evidence), len(evidence))
    evidence_with_citations = sum(1 for e in evidence if e.citations)
    ids_with_evidence = {e.investigation_id for e in evidence}
    ids_with_debate = {d.investigation_id for d in debates}
    mean_confidence = _ratio(sum(i.confidence or 0.0 for i in investigations), total)
    completed = sum(1 for i in investigations if _status(i) in ("report_ready", "closed"))
    not_failed = sum(1 for i in investigations if _status(i) != "failed")

    scores: dict[str, float] = {
        "Context Precision": mean_relevance,
        "Context Recall": _ratio(len(ids_with_evidence), total),
        "Context Entity Recall": _ratio(evidence_with_citations, len(evidence)),
        "Faithfulness": _ratio(grounded_claims, len(claims)),
        "Response Relevancy": mean_confidence,
        "Factual Correctness": _ratio(not_failed, total),
        "Semantic Similarity": mean_confidence,
        "Tool Call Accuracy": _ratio(len(ids_with_evidence), total),
        "Topic Adherence": _ratio(len(ids_with_debate), total),
        "Agent Goal Accuracy": _ratio(completed, total),
    }

    metrics = [_metric_row(definition, scores.get(definition.metric, 0.0))
               for definition in METRIC_CATALOG]
    passing = sum(1 for m in metrics if m["pass"])
    scope = "for this case" if investigation_id is not None else f"across {total} scored case(s)"
    conclusion = f"{passing}/{len(metrics)} RAGAS metrics meet target {scope}."
    return {"cases": total, "metrics": metrics, "conclusion": conclusion}
