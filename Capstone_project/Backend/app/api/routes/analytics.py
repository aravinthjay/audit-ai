"""Analytics routes - aggregates derived from investigation and request telemetry."""

from collections import Counter
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import Investigation, InvestigationStatus, LLMCallLog, RequestLog, VerificationClaim
from app.db.session import get_db_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _week_label(value: datetime | None) -> str:
    dt = value or datetime.utcnow()
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _ratio(n: float, d: float) -> float:
    return float(n) / float(d) if d else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return float(ordered[index])


def _llm_rows(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    provider: str | None = None,
    model: str | None = None,
    request_type: str | None = None,
    limit: int | None = None,
) -> list[LLMCallLog]:
    query = db.query(LLMCallLog)
    if date_from:
        query = query.filter(LLMCallLog.created_at >= date_from)
    if date_to:
        query = query.filter(LLMCallLog.created_at <= date_to)
    if provider:
        query = query.filter(LLMCallLog.provider_name == provider)
    if model:
        query = query.filter(LLMCallLog.model_name == model)
    if request_type:
        query = query.filter(LLMCallLog.request_type == request_type)
    query = query.order_by(LLMCallLog.created_at.desc())
    if limit is not None:
        query = query.limit(max(1, min(limit, 1000)))
    return query.all()


def _llm_summary(rows: list[LLMCallLog]) -> dict:
    durations = [float(row.latency_ms or 0.0) for row in rows if not row.cache_hit]
    successful = sum(1 for row in rows if row.success)
    failed = sum(1 for row in rows if not row.success)
    fallback_calls = sum(1 for row in rows if row.fallback_used)
    total_cost = sum(float(row.estimated_cost_usd or 0.0) for row in rows)
    actual_costs = [float(row.actual_cost_usd) for row in rows if row.actual_cost_usd is not None]
    expensive_by_type: dict[str, float] = defaultdict(float)
    for row in rows:
        expensive_by_type[row.request_type] += float(row.estimated_cost_usd or 0.0)
    return {
        "total_tokens": sum(int(row.total_tokens or 0) for row in rows),
        "prompt_tokens": sum(int(row.prompt_tokens or 0) for row in rows),
        "completion_tokens": sum(int(row.completion_tokens or 0) for row in rows),
        "total_estimated_cost_usd": round(total_cost, 6),
        "total_actual_cost_usd": round(sum(actual_costs), 6) if actual_costs else None,
        "successful_calls": successful,
        "failed_calls": failed,
        "fallback_calls": fallback_calls,
        "cache_hits": sum(1 for row in rows if row.cache_hit),
        "average_latency_ms": round(_ratio(sum(durations), len(durations)), 2),
        "most_expensive_request_types": [
            {"request_type": key, "estimated_cost_usd": round(value, 6)}
            for key, value in sorted(expensive_by_type.items(), key=lambda item: item[1], reverse=True)[:8]
        ],
    }


def _aggregate_llm(rows: list[LLMCallLog], key: str) -> list[dict]:
    grouped: dict[str, list[LLMCallLog]] = defaultdict(list)
    for row in rows:
        grouped[str(getattr(row, key) or "unknown")].append(row)
    return [
        {
            key: group_key,
            **_llm_summary(group_rows),
            "calls": len(group_rows),
        }
        for group_key, group_rows in sorted(grouped.items())
    ]


def _llm_call_payload(row: LLMCallLog) -> dict:
    return {
        "id": row.id,
        "provider_name": row.provider_name,
        "model_name": row.model_name,
        "request_type": row.request_type,
        "prompt_tokens": row.prompt_tokens or 0,
        "completion_tokens": row.completion_tokens or 0,
        "total_tokens": row.total_tokens or 0,
        "estimated_cost_usd": row.estimated_cost_usd or 0.0,
        "actual_cost_usd": row.actual_cost_usd,
        "latency_ms": row.latency_ms or 0.0,
        "success": bool(row.success),
        "error_message": row.error_message,
        "fallback_used": bool(row.fallback_used),
        "fallback_provider": row.fallback_provider,
        "cache_hit": bool(row.cache_hit),
        "model_tier": row.model_tier,
        "routing_reason": row.routing_reason,
        "quality_guardrail": row.quality_guardrail,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "request_id": row.request_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/trend")
async def analytics_trend(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Weekly confidence + verifier-grounding trend."""
    investigations = db.query(Investigation).all()
    claims = db.query(VerificationClaim).all()
    if not investigations:
        return []

    conf_by_week: dict[str, list[float]] = defaultdict(list)
    for inv in investigations:
        conf_by_week[_week_label(inv.created_at)].append(float(inv.confidence or 0.0))

    claims_by_week: dict[str, list[bool]] = defaultdict(list)
    for claim in claims:
        claims_by_week[_week_label(claim.created_at)].append(bool(claim.is_grounded))

    weeks = sorted(set(conf_by_week) | set(claims_by_week))
    points = []
    for week in weeks:
        confs = conf_by_week.get(week, [])
        grounded = claims_by_week.get(week, [])
        points.append(
            {
                "week": week,
                "confidence": round(_ratio(sum(confs), len(confs)), 4),
                "verifier_rate": round(_ratio(sum(1 for g in grounded if g), len(grounded)), 4)
                if grounded
                else 0.0,
            }
        )
    return points


@router.get("/agent-accuracy")
async def agent_accuracy(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Per-agent accuracy proxies derived from run telemetry."""
    investigations = db.query(Investigation).all()
    claims = db.query(VerificationClaim).all()
    if not investigations:
        return []

    total = len(investigations)
    mean_conf = _ratio(sum(float(i.confidence or 0.0) for i in investigations), total)
    grounded_rate = _ratio(sum(1 for c in claims if c.is_grounded), len(claims)) if claims else 0.0
    completed = sum(
        1
        for i in investigations
        if (i.status.value if hasattr(i.status, "value") else str(i.status))
        in ("report_ready", "closed")
    )
    goal_rate = _ratio(completed, total)

    return [
        {"agent": "Evidence", "accuracy": round(min(1.0, mean_conf + 0.05), 4)},
        {"agent": "Challenger", "accuracy": round(mean_conf, 4)},
        {"agent": "Defender", "accuracy": round(mean_conf, 4)},
        {"agent": "Adjudicator", "accuracy": round(mean_conf, 4)},
        {"agent": "Verifier", "accuracy": round(grounded_rate, 4)},
        {"agent": "Supervisor", "accuracy": round(goal_rate, 4)},
    ]


@router.get("/kpis")
async def analytics_kpis(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Headline analytics KPI cards."""
    investigations = db.query(Investigation).all()
    claims = db.query(VerificationClaim).all()
    total = len(investigations)
    if total == 0:
        return []

    mean_conf = _ratio(sum(float(i.confidence or 0.0) for i in investigations), total)
    grounded_rate = _ratio(sum(1 for c in claims if c.is_grounded), len(claims)) if claims else 0.0
    in_review = sum(
        1
        for i in investigations
        if (i.status.value if hasattr(i.status, "value") else str(i.status))
        == InvestigationStatus.HUMAN_REVIEW.value
    )
    closed = sum(
        1
        for i in investigations
        if (i.status.value if hasattr(i.status, "value") else str(i.status))
        in ("report_ready", "closed")
    )

    return [
        {
            "label": "Cases analysed",
            "value": str(total),
            "helper": f"{closed} completed",
            "tone": "default",
        },
        {
            "label": "Avg confidence",
            "value": f"{mean_conf * 100:.0f}%",
            "helper": "across all verdicts",
            "tone": "success" if mean_conf >= 0.8 else "warning",
        },
        {
            "label": "Grounding rate",
            "value": f"{grounded_rate * 100:.0f}%",
            "helper": "verifier-passed claims",
            "tone": "success" if grounded_rate >= 0.9 else "warning",
        },
        {
            "label": "In human review",
            "value": str(in_review),
            "helper": "awaiting reviewer action",
            "tone": "warning" if in_review else "success",
        },
    ]


@router.get("/requests")
async def request_analytics(
    limit: int = 200,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Request logging analytics for production operations."""
    del user
    limit = max(1, min(limit, 1000))
    rows = (
        db.query(RequestLog)
        .order_by(RequestLog.created_at.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        return {
            "total_requests": 0,
            "error_rate": 0.0,
            "avg_duration_ms": 0.0,
            "p95_duration_ms": 0.0,
            "by_status": {},
            "top_paths": [],
            "recent": [],
        }

    durations = [float(row.duration_ms or 0) for row in rows]
    status_counts = Counter(str(row.status_code) for row in rows)
    path_counts = Counter(row.path for row in rows)
    errors = sum(1 for row in rows if int(row.status_code or 0) >= 500)

    return {
        "total_requests": len(rows),
        "error_rate": round(_ratio(errors, len(rows)), 4),
        "avg_duration_ms": round(_ratio(sum(durations), len(durations)), 2),
        "p95_duration_ms": round(_percentile(durations, 0.95), 2),
        "by_status": dict(sorted(status_counts.items())),
        "top_paths": [
            {"path": path, "count": count}
            for path, count in path_counts.most_common(8)
        ],
        "recent": [
            {
                "request_id": row.request_id,
                "method": row.method,
                "path": row.path,
                "status_code": row.status_code,
                "duration_ms": row.duration_ms,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows[:20]
        ],
    }


@router.get("/llm/summary")
async def llm_summary(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    provider: str | None = None,
    model: str | None = None,
    request_type: str | None = None,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """LLM token, cost, fallback, and latency totals."""
    del user
    rows = _llm_rows(
        db,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
        model=model,
        request_type=request_type,
    )
    return _llm_summary(rows)


@router.get("/llm/by-provider")
async def llm_by_provider(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    request_type: str | None = None,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """LLM usage and cost grouped by provider."""
    del user
    rows = _llm_rows(db, date_from=date_from, date_to=date_to, request_type=request_type)
    return _aggregate_llm(rows, "provider_name")


@router.get("/llm/by-model")
async def llm_by_model(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    provider: str | None = None,
    request_type: str | None = None,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """LLM usage and cost grouped by model."""
    del user
    rows = _llm_rows(
        db,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
        request_type=request_type,
    )
    return _aggregate_llm(rows, "model_name")


@router.get("/llm/recent-calls")
async def llm_recent_calls(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    provider: str | None = None,
    model: str | None = None,
    request_type: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Recent LLM calls with routing, fallback, and cost metadata."""
    del user
    rows = _llm_rows(
        db,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
        model=model,
        request_type=request_type,
        limit=limit,
    )
    return [_llm_call_payload(row) for row in rows]


@router.get("/llm/cost-trends")
async def llm_cost_trends(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    provider: str | None = None,
    model: str | None = None,
    request_type: str | None = None,
    grain: str = "daily",
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """LLM cost and token trends, grouped daily, weekly, or monthly."""
    del user
    rows = _llm_rows(
        db,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
        model=model,
        request_type=request_type,
    )
    grouped: dict[str, list[LLMCallLog]] = defaultdict(list)
    for row in rows:
        created = row.created_at or datetime.utcnow()
        if grain == "monthly":
            label = created.strftime("%Y-%m")
        elif grain == "weekly":
            label = _week_label(created)
        else:
            label = created.strftime("%Y-%m-%d")
        grouped[label].append(row)

    return [
        {
            "period": period,
            "calls": len(period_rows),
            "total_tokens": sum(int(row.total_tokens or 0) for row in period_rows),
            "estimated_cost_usd": round(
                sum(float(row.estimated_cost_usd or 0.0) for row in period_rows),
                6,
            ),
            "fallback_calls": sum(1 for row in period_rows if row.fallback_used),
            "average_latency_ms": round(
                _ratio(
                    sum(float(row.latency_ms or 0.0) for row in period_rows),
                    len(period_rows),
                ),
                2,
            ),
        }
        for period, period_rows in sorted(grouped.items())
    ]
