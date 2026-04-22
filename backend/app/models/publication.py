import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Publication(BaseModel):
    __tablename__ = "publications"
    __table_args__ = (
        Index("ix_publications_session_created", "review_session_id", "created_at"),
        Index("ix_publications_status", "status"),
    )

    review_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_system: Mapped[str] = mapped_column(String(50), nullable=False)
    target_object_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_comment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    publication_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="success")
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    review_session = relationship("ReviewSession", back_populates="publications")
