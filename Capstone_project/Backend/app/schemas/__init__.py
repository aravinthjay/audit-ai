"""
Pydantic request/response schemas for the API surface.
"""

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvestigationCreate(BaseModel):
    transaction_id: str = Field(..., min_length=1, max_length=100)
    vendor: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    materiality: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = None
    owner: Optional[str] = None


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    transaction_id: str
    vendor: str
    category: str
    amount: float
    risk: Optional[str] = None
    confidence: float = 0.0
    flags: list[str] = Field(default_factory=list)
    status: str
    owner: Optional[str] = None
    reviewer: Optional[str] = None
    posted_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    materiality: Optional[float] = None
    description: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class InvestigationList(BaseModel):
    total: int
    skip: int
    limit: int
    investigations: list[InvestigationOut]


class InvestigationDeleteResponse(BaseModel):
    deleted_count: int
    investigation_ids: list[str] = Field(default_factory=list)
    message: str


class ExecuteResponse(BaseModel):
    investigation_id: str
    task_id: Optional[str] = None
    status: str
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None
    role: Literal["analyst", "reviewer", "partner", "admin"] = "analyst"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool


class StatsSummary(BaseModel):
    """Aggregate investigation statistics for the dashboard."""

    total: int
    avg_confidence: float
    by_risk: dict[str, int]
    by_status: dict[str, int]
    auto_cleared: int
    in_review: int
    manual: int


class AgentHealthOut(BaseModel):
    """Workload-derived agent health for the dashboard."""

    label: str
    state: str
    latency: str
    load: float = Field(..., ge=0.0, le=1.0)


class PipelineStepOut(BaseModel):
    """Case-specific agent workflow step."""

    id: str
    role: str
    state: str
    detail: str
    latency: Optional[str] = None
    confidence: Optional[float] = None
    token_usage: int = 0
    cost: float = 0.0
    attempt: int = 1
    expanded_detail: str


class AppSettingsOut(BaseModel):
    """Runtime governance settings exposed to the UI."""

    reasoning_model: str
    report_model: str
    auto_clear_threshold: float
    reviewer_threshold: float
    materiality: float
    segregation_of_duties: bool
    immutable_audit_log: bool
    debate_round_cap: int
    api_key_vault: str
    theme: Literal["system", "light", "dark"]
    display_currency: str
    notifications: bool
    audit_retention_years: int
    ip_allowlist: bool
    estimated_agent_run_cost_usd: float


LLMProviderName = Literal["anthropic", "groq", "openai"]


class LLMProviderStatusOut(BaseModel):
    id: LLMProviderName
    label: str
    configured: bool
    reasoning_model: str
    lightweight_model: str
    missing_env: Optional[str] = None


class LLMSettingsOut(BaseModel):
    default_provider: LLMProviderName
    active_provider: LLMProviderName
    fallback_enabled: bool
    fallback_order: list[LLMProviderName]
    providers: list[LLMProviderStatusOut]


class LLMSettingsUpdate(BaseModel):
    default_provider: LLMProviderName
    fallback_enabled: bool
    fallback_order: list[LLMProviderName] = Field(default_factory=list)

    @field_validator("fallback_order")
    @classmethod
    def _dedupe_fallback_order(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for provider in value:
            if provider not in seen:
                seen.add(provider)
                deduped.append(provider)
        return deduped


class IntakeRuleStatOut(BaseModel):
    rule: str
    count: int
    tone: Literal["danger", "warning", "info"]


class FlaggedRowOut(BaseModel):
    txn_id: str
    vendor: str
    account: str
    amount: str
    rules: list[str] = Field(default_factory=list)


class IntakeSummaryOut(BaseModel):
    file_name: str
    rows_ingested: int
    flagged: int
    cleared: int
    parse_errors: int
    est_cost_usd: float
    columns: list[str] = Field(default_factory=list)
    rule_stats: list[IntakeRuleStatOut] = Field(default_factory=list)
    flagged_rows: list[FlaggedRowOut] = Field(default_factory=list)


class DebateMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    round: int
    speaker: str
    message: str
    token_count: int = 0
    confidence: Optional[float] = None
    created_at: datetime


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    content: str
    citations: list[Any] = Field(default_factory=list)
    relevance_score: float = 0.0
    created_at: datetime


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_text: str
    is_grounded: bool = False
    explanation: Optional[str] = None
    supporting_evidence: list[Any] = Field(default_factory=list)
    created_at: datetime


EvidenceVerificationStatus = Literal[
    "VERIFIED",
    "FLAGGED",
    "API_UNAVAILABLE",
    "NEEDS_MANUAL_REVIEW",
]


class ClaimEvidenceVerifyRequest(BaseModel):
    category: Optional[str] = Field(default=None, max_length=100)
    claimed_amount: Optional[float] = Field(default=None, gt=0)
    vendor: Optional[str] = Field(default=None, max_length=255)
    gstin: Optional[str] = Field(default=None, max_length=20)
    route_from: Optional[str] = Field(default=None, max_length=120)
    route_to: Optional[str] = Field(default=None, max_length=120)
    service_date: Optional[date] = None
    invoice_date: Optional[date] = None
    quantity: Optional[float] = Field(default=None, gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    location: Optional[str] = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class ClaimEvidencePreviewRequest(ClaimEvidenceVerifyRequest):
    category: str = Field(..., min_length=1, max_length=100)
    claimed_amount: float = Field(..., gt=0)


class ClaimEvidenceVerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    claim_id: Optional[str] = None
    category: str
    claimed_amount: float
    fetched_amount: Optional[float] = None
    min_acceptable_amount: Optional[float] = None
    max_acceptable_amount: Optional[float] = None
    difference_amount: Optional[float] = None
    difference_percentage: Optional[float] = None
    tolerance_percentage: float
    provider_name: str
    provider_reference_id: Optional[str] = None
    verification_status: EvidenceVerificationStatus
    confidence_score: float
    reason: str
    created_at: datetime
    updated_at: datetime


class AuditEventOut(BaseModel):
    id: str
    type: str
    data: dict[str, Any]
    hash: Optional[str] = None
    prev_hash: Optional[str] = None
    sequence: Optional[int] = None


class ReviewQueueOut(BaseModel):
    id: str
    investigation_id: str
    title: str
    risk: Optional[str] = None
    confidence: float = 0.0
    due_at: Optional[datetime] = None
    queue: str = "reviewer"
    status: str = "pending"
    assigned_to: Optional[str] = None
    priority: int = 3
    notes: Optional[str] = None


class ReviewActionRequest(BaseModel):
    actor: Optional[str] = None
    comment: Optional[str] = None


class ReviewActionResponse(BaseModel):
    investigation_id: str
    action: str
    status: str
    message: str


class RagasMetricOut(BaseModel):
    """A single RAGAS metric score (retrieval / generation / agentic)."""

    model_config = ConfigDict(populate_by_name=True)

    metric: str
    category: Literal["retrieval", "generation", "agentic"]
    score: float = Field(..., ge=0.0, le=1.0)
    target: float = Field(..., ge=0.0, le=1.0)
    # `pass` is a Python keyword; expose it as JSON "pass" via an alias.
    passed: bool = Field(..., alias="pass")
    helper: str


class EvaluationSummaryOut(BaseModel):
    """RAGAS evaluation summary for the /evaluation dashboard."""

    cases: int
    metrics: list[RagasMetricOut]
    conclusion: str
