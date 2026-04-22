"""init core tables

Revision ID: 0001_init_core
Revises: 
Create Date: 2026-04-23 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_init_core"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_objects",
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("external_system", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_system", "external_id", name="uq_source_external"),
    )
    op.create_index("ix_source_objects_source_type", "source_objects", ["source_type"])

    op.create_table(
        "connector_credentials",
        sa.Column("connector_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_connector_credentials_type_active", "connector_credentials", ["connector_type", "is_active"])

    op.create_table(
        "source_snapshots",
        sa.Column("source_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("raw_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("normalized_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_object_id"], ["source_objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_object_id", "version_no", name="uq_snapshot_version"),
    )
    op.create_index("ix_source_snapshots_source_hash", "source_snapshots", ["source_object_id", "content_hash"])

    op.create_table(
        "review_sessions",
        sa.Column("source_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("last_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_review_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_publication_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("iteration_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("recheck_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_input_hash", sa.String(length=128), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_object_id"], ["source_objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_object_id"),
    )
    op.create_index("ix_review_sessions_status", "review_sessions", ["status"])

    op.create_table(
        "review_runs",
        sa.Column("review_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("output_hash", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["review_session_id"], ["review_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["source_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_runs_session_created", "review_runs", ["review_session_id", "created_at"])
    op.create_index("ix_review_runs_status", "review_runs", ["status"])

    op.create_table(
        "findings",
        sa.Column("review_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_detected_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_seen_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_key", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("resolution_type", sa.String(length=50), nullable=True),
        sa.Column("times_repeated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_tone_level", sa.String(length=50), nullable=False, server_default="strict"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["review_session_id"], ["review_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_session_id", "finding_key", name="uq_session_finding_key"),
    )
    op.create_index("ix_findings_session_status", "findings", ["review_session_id", "status"])
    op.create_index("ix_findings_category", "findings", ["category"])

    op.create_table(
        "publications",
        sa.Column("review_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_system", sa.String(length=50), nullable=False),
        sa.Column("target_object_id", sa.String(length=255), nullable=False),
        sa.Column("external_comment_id", sa.String(length=255), nullable=True),
        sa.Column("published_body_markdown", sa.Text(), nullable=False),
        sa.Column("publication_mode", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="success"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["review_run_id"], ["review_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_session_id"], ["review_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publications_session_created", "publications", ["review_session_id", "created_at"])
    op.create_index("ix_publications_status", "publications", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_event_created", "audit_logs", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_event_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_publications_status", table_name="publications")
    op.drop_index("ix_publications_session_created", table_name="publications")
    op.drop_table("publications")
    op.drop_index("ix_findings_category", table_name="findings")
    op.drop_index("ix_findings_session_status", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_review_runs_status", table_name="review_runs")
    op.drop_index("ix_review_runs_session_created", table_name="review_runs")
    op.drop_table("review_runs")
    op.drop_index("ix_review_sessions_status", table_name="review_sessions")
    op.drop_table("review_sessions")
    op.drop_index("ix_source_snapshots_source_hash", table_name="source_snapshots")
    op.drop_table("source_snapshots")
    op.drop_index("ix_connector_credentials_type_active", table_name="connector_credentials")
    op.drop_table("connector_credentials")
    op.drop_index("ix_source_objects_source_type", table_name="source_objects")
    op.drop_table("source_objects")
