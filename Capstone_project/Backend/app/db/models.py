"""
SQLAlchemy ORM models for PostgreSQL.
Defines tables for investigations, debate transcripts, evidence, verification, and audit logs.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


class RiskLevel(str, enum.Enum):
    """Risk assessment levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CLEARED = "cleared"


class InvestigationStatus(str, enum.Enum):
    """Investigation pipeline stages."""

    INTAKE = "intake"
    COLLECTING_EVIDENCE = "collecting_evidence"
    AGENT_DEBATE = "agent_debate"
    VERIFICATION = "verification"
    HUMAN_REVIEW = "human_review"
    REPORT_READY = "report_ready"
    CLOSED = "closed"
    FAILED = "failed"


class WorkState(str, enum.Enum):
    """Agent work state."""

    IDLE = "idle"
    RUNNING = "running"
    QUEUED = "queued"
    DONE = "done"
    FAILED = "failed"
    RETRY = "retry"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    REVIEW = "review"


class Investigation(Base):
    """Investigation case record."""

    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=_uuid)
    transaction_id = Column(String(100), nullable=False, index=True)
    vendor = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    confidence = Column(Float, default=0.0)
    risk = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM, nullable=False, index=True)
    flags = Column(JSON, default=list)
    status = Column(
        Enum(InvestigationStatus),
        default=InvestigationStatus.INTAKE,
        nullable=False,
        index=True,
    )
    owner = Column(String(100), nullable=True)
    reviewer = Column(String(100), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    materiality = Column(Float, default=50000.0)
    description = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    states = relationship(
        "InvestigationState", back_populates="investigation", cascade="all, delete-orphan"
    )
    debate_transcripts = relationship(
        "DebateTranscript", back_populates="investigation", cascade="all, delete-orphan"
    )
    evidence_artifacts = relationship(
        "EvidenceArtifact", back_populates="investigation", cascade="all, delete-orphan"
    )
    verification_claims = relationship(
        "VerificationClaim", back_populates="investigation", cascade="all, delete-orphan"
    )
    third_party_evidence_verifications = relationship(
        "ThirdPartyEvidenceVerification",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("idx_transaction_vendor", "transaction_id", "vendor"),)


class InvestigationState(Base):
    """State checkpoint for investigation execution (LangGraph state)."""

    __tablename__ = "investigation_states"

    id = Column(String(36), primary_key=True, default=_uuid)
    investigation_id = Column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    phase = Column(String(50), nullable=False)
    state_json = Column(JSON, nullable=False)
    checkpoint_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    investigation = relationship("Investigation", back_populates="states")

    __table_args__ = (Index("idx_investigation_phase", "investigation_id", "phase"),)


class DebateTranscript(Base):
    """Debate round transcript between Challenger and Defender."""

    __tablename__ = "debate_transcripts"

    id = Column(String(36), primary_key=True, default=_uuid)
    investigation_id = Column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    round = Column(Integer, nullable=False)
    speaker = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    investigation = relationship("Investigation", back_populates="debate_transcripts")

    __table_args__ = (Index("idx_investigation_round", "investigation_id", "round"),)


class EvidenceArtifact(Base):
    """Evidence collected and aggregated by Evidence agent."""

    __tablename__ = "evidence_artifacts"

    id = Column(String(36), primary_key=True, default=_uuid)
    investigation_id = Column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    source = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list)
    relevance_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    investigation = relationship("Investigation", back_populates="evidence_artifacts")

    __table_args__ = (Index("idx_investigation_source", "investigation_id", "source"),)


class VerificationClaim(Base):
    """Claim verification record from Verifier agent."""

    __tablename__ = "verification_claims"

    id = Column(String(36), primary_key=True, default=_uuid)
    investigation_id = Column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    claim_text = Column(Text, nullable=False)
    is_grounded = Column(Boolean, default=False)
    explanation = Column(Text, nullable=True)
    supporting_evidence = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    investigation = relationship("Investigation", back_populates="verification_claims")


class ThirdPartyEvidenceVerification(Base):
    """External benchmark verification for a claim amount."""

    __tablename__ = "third_party_evidence_verifications"

    id = Column(String(36), primary_key=True, default=_uuid)
    claim_id = Column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(String(100), nullable=False, index=True)
    claimed_amount = Column(Float, nullable=False)
    fetched_amount = Column(Float, nullable=True)
    min_acceptable_amount = Column(Float, nullable=True)
    max_acceptable_amount = Column(Float, nullable=True)
    difference_amount = Column(Float, nullable=True)
    difference_percentage = Column(Float, nullable=True)
    tolerance_percentage = Column(Float, nullable=False)
    provider_name = Column(String(100), nullable=False)
    provider_reference_id = Column(String(255), nullable=True)
    verification_status = Column(String(50), nullable=False, index=True)
    confidence_score = Column(Float, default=0.0)
    reason = Column(Text, nullable=False)
    raw_provider_response_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    investigation = relationship(
        "Investigation", back_populates="third_party_evidence_verifications"
    )

    __table_args__ = (
        Index("idx_claim_evidence_status", "claim_id", "verification_status"),
    )


class AuditLog(Base):
    """Immutable audit log with a SHA256 hash chain."""

    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=_uuid)
    investigation_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    details = Column(JSON, nullable=False)
    hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=True)
    sequence = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_investigation_event", "investigation_id", "event_type"),
        Index("idx_investigation_sequence", "investigation_id", "sequence"),
    )


class RequestLog(Base):
    """HTTP request telemetry for production analytics and auditability."""

    __tablename__ = "request_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    request_id = Column(String(64), nullable=False, index=True)
    method = Column(String(12), nullable=False)
    path = Column(String(500), nullable=False, index=True)
    status_code = Column(Integer, nullable=False, index=True)
    duration_ms = Column(Float, nullable=False)
    client_host = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    user_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_request_logs_created_status", "created_at", "status_code"),
        Index("idx_request_logs_path_created", "path", "created_at"),
    )


class RuntimeSetting(Base):
    """Persisted runtime settings that can be changed without app restart."""

    __tablename__ = "runtime_settings"

    key = Column(String(100), primary_key=True)
    value_json = Column(JSON, nullable=False)
    updated_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LLMCallLog(Base):
    """Per-call LLM usage telemetry for cost, latency, and fallback analytics."""

    __tablename__ = "llm_call_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    provider_name = Column(String(50), nullable=False, index=True)
    model_name = Column(String(120), nullable=False, index=True)
    request_type = Column(String(100), nullable=False, index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    actual_cost_usd = Column(Float, nullable=True)
    latency_ms = Column(Float, default=0.0)
    success = Column(Boolean, default=False, index=True)
    error_message = Column(Text, nullable=True)
    fallback_used = Column(Boolean, default=False, index=True)
    fallback_provider = Column(String(50), nullable=True)
    cache_hit = Column(Boolean, default=False)
    model_tier = Column(String(30), nullable=False, default="standard")
    routing_reason = Column(Text, nullable=True)
    quality_guardrail = Column(Text, nullable=True)
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_llm_provider_created", "provider_name", "created_at"),
        Index("idx_llm_model_created", "model_name", "created_at"),
        Index("idx_llm_request_type_created", "request_type", "created_at"),
        Index("idx_llm_success_created", "success", "created_at"),
    )


class ReviewQueueItem(Base):
    """Human review queue."""

    __tablename__ = "review_queue"

    id = Column(String(36), primary_key=True, default=_uuid)
    investigation_id = Column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    assigned_to = Column(String(100), nullable=True)
    priority = Column(Integer, default=1)
    status = Column(String(50), default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_assigned_status", "assigned_to", "status"),
        Index("idx_investigation_queue", "investigation_id"),
    )


class VectorEmbedding(Base):
    """Vector embeddings for RAG (pgvector integration)."""

    __tablename__ = "vector_embeddings"

    id = Column(String(36), primary_key=True, default=_uuid)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)
    # "metadata" is reserved by SQLAlchemy's declarative API; attribute is
    # named meta and maps to the "meta" DB column.
    meta = Column("meta", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (Index("idx_source_type_id", "source_type", "source_id"),)


class User(Base):
    """Application user for authentication."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="analyst")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
