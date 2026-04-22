"""add publication tracking fk placeholders

Revision ID: 0003_pub_track
Revises: 0002_review_iter
Create Date: 2026-04-23 00:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_pub_track"
down_revision: str | None = "0002_review_iter"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("review_sessions") as batch_op:
        batch_op.create_foreign_key(
            "fk_review_sessions_last_snapshot",
            "source_snapshots",
            ["last_snapshot_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_review_sessions_last_review_run",
            "review_runs",
            ["last_review_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_review_sessions_current_publication",
            "publications",
            ["current_publication_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("review_sessions") as batch_op:
        batch_op.drop_constraint("fk_review_sessions_current_publication", type_="foreignkey")
        batch_op.drop_constraint("fk_review_sessions_last_review_run", type_="foreignkey")
        batch_op.drop_constraint("fk_review_sessions_last_snapshot", type_="foreignkey")
