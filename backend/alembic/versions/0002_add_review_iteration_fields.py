"""add review iteration fields

Revision ID: 0002_review_iter
Revises: 0001_init_core
Create Date: 2026-04-23 00:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_review_iter"
down_revision: str | None = "0001_init_core"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("review_sessions", "max_iterations", server_default=None)
    op.alter_column("review_sessions", "iteration_count", server_default=None)
    op.alter_column("findings", "times_repeated", server_default=None)


def downgrade() -> None:
    op.alter_column("findings", "times_repeated", server_default="0")
    op.alter_column("review_sessions", "iteration_count", server_default="0")
    op.alter_column("review_sessions", "max_iterations", server_default="3")
