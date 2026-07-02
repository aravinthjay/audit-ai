"""Case-intake routes derived from persisted imported investigations."""

import re
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.models import Investigation
from app.db.session import get_db_session
from app.schemas import FlaggedRowOut, IntakeRuleStatOut, IntakeSummaryOut

router = APIRouter(prefix="/intake", tags=["intake"])

_RULE_TONES: dict[str, str] = {
    "materiality": "danger",
    "fx outlier": "warning",
    "round-number": "warning",
    "segregation of duties": "danger",
    "duplicate": "info",
    "unknown vendor": "danger",
    "off-hours": "info",
}


def _format_amount(value: float) -> str:
    currency = settings.DISPLAY_CURRENCY.upper()
    if currency == "USD":
        return f"${value:,.0f}"
    return f"{currency} {value:,.0f}"


def _file_name(description: str | None) -> str | None:
    if not description:
        return None
    match = re.search(
        r"Created from intake file\s+(.+?)(?:\.\s+Rules fired:|\.\s+Source account:|$)",
        description,
    )
    return match.group(1).strip() if match else None


def _rules(description: str | None, flags: list[str] | None) -> list[str]:
    text = description or ""
    match = re.search(r"Rules fired:\s+(.+?)(?:\.\s+Source account:|$)", text)
    if match:
        return [item.strip() for item in match.group(1).split(",") if item.strip()]
    return [item for item in (flags or []) if not item.startswith("third_party_evidence:")]


def _rule_label(rule: str) -> str:
    normalized = rule.strip().lower()
    if normalized == "materiality":
        return f"Materiality >= {_format_amount(settings.DEFAULT_MATERIALITY_THRESHOLD)}"
    return normalized.replace("-", " ").title()


@router.get("/summary", response_model=IntakeSummaryOut | None)
async def intake_summary(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Summarize investigations created by the ledger intake workflow."""
    del user
    rows = (
        db.query(Investigation)
        .filter(Investigation.owner == "intake")
        .order_by(Investigation.created_at.desc())
        .all()
    )
    if not rows:
        return None

    file_names = Counter(filter(None, (_file_name(row.description) for row in rows)))
    file_name = file_names.most_common(1)[0][0] if file_names else "Persisted intake cases"
    rule_counts: Counter[str] = Counter()
    flagged_rows: list[FlaggedRowOut] = []

    for row in rows:
        rules = _rules(row.description, row.flags)
        rule_counts.update(rule.strip().lower() for rule in rules)
        flagged_rows.append(
            FlaggedRowOut(
                txn_id=row.transaction_id,
                vendor=row.vendor,
                account=row.category,
                amount=_format_amount(float(row.amount or 0)),
                rules=rules,
            )
        )

    rule_stats = [
        IntakeRuleStatOut(
            rule=_rule_label(rule),
            count=count,
            tone=_RULE_TONES.get(rule, "info"),
        )
        for rule, count in sorted(rule_counts.items())
    ]

    return IntakeSummaryOut(
        file_name=file_name,
        rows_ingested=len(rows),
        flagged=len(rows),
        cleared=0,
        parse_errors=0,
        est_cost_usd=round(len(rows) * settings.ESTIMATED_AGENT_RUN_COST_USD, 2),
        columns=["transaction_id", "vendor", "category", "amount", "description"],
        rule_stats=rule_stats,
        flagged_rows=flagged_rows,
    )
