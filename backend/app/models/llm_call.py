import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class LLMCall(BaseModel):
    __tablename__ = "llm_calls"
    __table_args__ = (
        Index("ix_llm_calls_review_run_created", "review_run_id", "created_at"),
        Index("ix_llm_calls_status", "status"),
        Index("ix_llm_calls_error_type", "error_type"),
    )

    review_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="started")
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parsed_response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    review_run = relationship("ReviewRun", back_populates="llm_calls")
