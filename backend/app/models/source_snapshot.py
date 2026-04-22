import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SourceSnapshot(BaseModel):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        UniqueConstraint("source_object_id", "version_no", name="uq_snapshot_version"),
        Index("ix_source_snapshots_source_hash", "source_object_id", "content_hash"),
    )

    source_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_objects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_text: Mapped[str] = mapped_column(nullable=False)
    normalized_metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(nullable=False)

    source_object = relationship("SourceObject", back_populates="snapshots")
    runs = relationship("ReviewRun", back_populates="snapshot")
