"""add source connector credential

Revision ID: 0004_src_conn
Revises: 0003_pub_track
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_src_conn"
down_revision = "0003_pub_track"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source_objects",
        sa.Column("connector_credential_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_source_objects_connector_credential",
        "source_objects",
        "connector_credentials",
        ["connector_credential_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_source_objects_connector_credential", "source_objects", type_="foreignkey")
    op.drop_column("source_objects", "connector_credential_id")
