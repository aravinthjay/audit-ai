"""add third-party evidence verification table

Revision ID: 20260630_0001
Revises:
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260630_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "third_party_evidence_verifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("claim_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("claimed_amount", sa.Float(), nullable=False),
        sa.Column("fetched_amount", sa.Float(), nullable=True),
        sa.Column("min_acceptable_amount", sa.Float(), nullable=True),
        sa.Column("max_acceptable_amount", sa.Float(), nullable=True),
        sa.Column("difference_amount", sa.Float(), nullable=True),
        sa.Column("difference_percentage", sa.Float(), nullable=True),
        sa.Column("tolerance_percentage", sa.Float(), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("provider_reference_id", sa.String(length=255), nullable=True),
        sa.Column("verification_status", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("raw_provider_response_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_third_party_evidence_verifications_claim_id"),
        "third_party_evidence_verifications",
        ["claim_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_third_party_evidence_verifications_category"),
        "third_party_evidence_verifications",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_third_party_evidence_verifications_created_at"),
        "third_party_evidence_verifications",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_third_party_evidence_verifications_verification_status"),
        "third_party_evidence_verifications",
        ["verification_status"],
        unique=False,
    )
    op.create_index(
        "idx_claim_evidence_status",
        "third_party_evidence_verifications",
        ["claim_id", "verification_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_claim_evidence_status", table_name="third_party_evidence_verifications")
    op.drop_index(
        op.f("ix_third_party_evidence_verifications_verification_status"),
        table_name="third_party_evidence_verifications",
    )
    op.drop_index(
        op.f("ix_third_party_evidence_verifications_created_at"),
        table_name="third_party_evidence_verifications",
    )
    op.drop_index(
        op.f("ix_third_party_evidence_verifications_category"),
        table_name="third_party_evidence_verifications",
    )
    op.drop_index(
        op.f("ix_third_party_evidence_verifications_claim_id"),
        table_name="third_party_evidence_verifications",
    )
    op.drop_table("third_party_evidence_verifications")
