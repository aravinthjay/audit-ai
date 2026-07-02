"""Third-party evidence verification package."""

from app.evidence_verification.service import (
    EvidenceVerificationService,
    STATUS_API_UNAVAILABLE,
    STATUS_FLAGGED,
    STATUS_NEEDS_MANUAL_REVIEW,
    STATUS_VERIFIED,
)

__all__ = [
    "EvidenceVerificationService",
    "STATUS_API_UNAVAILABLE",
    "STATUS_FLAGGED",
    "STATUS_NEEDS_MANUAL_REVIEW",
    "STATUS_VERIFIED",
]
