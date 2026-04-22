import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ReviewSession(BaseModel):
    __tablename__ = "review_sessions"
    __table_args__ = (Index("ix_review_sessions_status", "status"),)

    source_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_objects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    last_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_review_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    current_publication_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    iteration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    recheck_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_object = relationship("SourceObject", back_populates="review_session")
    runs = relationship("ReviewRun", back_populates="review_session")
    findings = relationship("Finding", back_populates="review_session")
    publications = relationship("Publication", back_populates="review_session")
