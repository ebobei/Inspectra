"""add llm call diagnostics

Revision ID: 0005_llm_calls
Revises: 0004_src_conn
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_llm_calls"
down_revision = "0004_src_conn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_calls",
        sa.Column("review_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("request_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_raw_text", sa.Text(), nullable=True),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("parsed_response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["review_run_id"], ["review_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_calls_review_run_created", "llm_calls", ["review_run_id", "created_at"], unique=False)
    op.create_index("ix_llm_calls_status", "llm_calls", ["status"], unique=False)
    op.create_index("ix_llm_calls_error_type", "llm_calls", ["error_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_llm_calls_error_type", table_name="llm_calls")
    op.drop_index("ix_llm_calls_status", table_name="llm_calls")
    op.drop_index("ix_llm_calls_review_run_created", table_name="llm_calls")
    op.drop_table("llm_calls")
