"""add request logging table

Revision ID: 20260701_0002
Revises: 20260630_0001
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0002"
down_revision: Union[str, None] = "20260630_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("method", sa.String(length=12), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("client_host", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_request_logs_created_at"), "request_logs", ["created_at"])
    op.create_index(op.f("ix_request_logs_path"), "request_logs", ["path"])
    op.create_index(op.f("ix_request_logs_request_id"), "request_logs", ["request_id"])
    op.create_index(op.f("ix_request_logs_status_code"), "request_logs", ["status_code"])
    op.create_index(op.f("ix_request_logs_user_id"), "request_logs", ["user_id"])
    op.create_index(
        "idx_request_logs_created_status",
        "request_logs",
        ["created_at", "status_code"],
    )
    op.create_index(
        "idx_request_logs_path_created",
        "request_logs",
        ["path", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_request_logs_path_created", table_name="request_logs")
    op.drop_index("idx_request_logs_created_status", table_name="request_logs")
    op.drop_index(op.f("ix_request_logs_user_id"), table_name="request_logs")
    op.drop_index(op.f("ix_request_logs_status_code"), table_name="request_logs")
    op.drop_index(op.f("ix_request_logs_request_id"), table_name="request_logs")
    op.drop_index(op.f("ix_request_logs_path"), table_name="request_logs")
    op.drop_index(op.f("ix_request_logs_created_at"), table_name="request_logs")
    op.drop_table("request_logs")
