import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Finding(BaseModel):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("review_session_id", "finding_key", name="uq_session_finding_key"),
        Index("ix_findings_session_status", "review_session_id", "status"),
        Index("ix_findings_category", "category"),
    )

    review_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    first_detected_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    last_seen_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    finding_key: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    resolution_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    times_repeated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_tone_level: Mapped[str] = mapped_column(String(50), nullable=False, default="strict")
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    review_session = relationship("ReviewSession", back_populates="findings")
