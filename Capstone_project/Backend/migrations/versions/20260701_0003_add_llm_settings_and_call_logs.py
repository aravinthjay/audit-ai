"""add LLM runtime settings and call logs

Revision ID: 20260701_0003
Revises: 20260701_0002
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0003"
down_revision: Union[str, None] = "20260701_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runtime_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(op.f("ix_runtime_settings_created_at"), "runtime_settings", ["created_at"])

    op.create_table(
        "llm_call_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("request_type", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("actual_cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), nullable=True),
        sa.Column("fallback_provider", sa.String(length=50), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=True),
        sa.Column("model_tier", sa.String(length=30), nullable=True),
        sa.Column("routing_reason", sa.Text(), nullable=True),
        sa.Column("quality_guardrail", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_call_logs_created_at"), "llm_call_logs", ["created_at"])
    op.create_index(op.f("ix_llm_call_logs_fallback_used"), "llm_call_logs", ["fallback_used"])
    op.create_index(op.f("ix_llm_call_logs_model_name"), "llm_call_logs", ["model_name"])
    op.create_index(op.f("ix_llm_call_logs_provider_name"), "llm_call_logs", ["provider_name"])
    op.create_index(op.f("ix_llm_call_logs_request_id"), "llm_call_logs", ["request_id"])
    op.create_index(op.f("ix_llm_call_logs_request_type"), "llm_call_logs", ["request_type"])
    op.create_index(op.f("ix_llm_call_logs_session_id"), "llm_call_logs", ["session_id"])
    op.create_index(op.f("ix_llm_call_logs_success"), "llm_call_logs", ["success"])
    op.create_index(op.f("ix_llm_call_logs_user_id"), "llm_call_logs", ["user_id"])
    op.create_index("idx_llm_model_created", "llm_call_logs", ["model_name", "created_at"])
    op.create_index("idx_llm_provider_created", "llm_call_logs", ["provider_name", "created_at"])
    op.create_index(
        "idx_llm_request_type_created",
        "llm_call_logs",
        ["request_type", "created_at"],
    )
    op.create_index("idx_llm_success_created", "llm_call_logs", ["success", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_llm_success_created", table_name="llm_call_logs")
    op.drop_index("idx_llm_request_type_created", table_name="llm_call_logs")
    op.drop_index("idx_llm_provider_created", table_name="llm_call_logs")
    op.drop_index("idx_llm_model_created", table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_user_id"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_success"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_session_id"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_request_type"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_request_id"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_provider_name"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_model_name"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_fallback_used"), table_name="llm_call_logs")
    op.drop_index(op.f("ix_llm_call_logs_created_at"), table_name="llm_call_logs")
    op.drop_table("llm_call_logs")
    op.drop_index(op.f("ix_runtime_settings_created_at"), table_name="runtime_settings")
    op.drop_table("runtime_settings")
