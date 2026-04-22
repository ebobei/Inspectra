import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SourceObject(BaseModel):
    __tablename__ = "source_objects"
    __table_args__ = (
        UniqueConstraint("external_system", "external_id", name="uq_source_external"),
        Index("ix_source_objects_source_type", "source_type"),
    )

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_system: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    connector_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("connector_credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    review_session = relationship("ReviewSession", back_populates="source_object", uselist=False)
    snapshots = relationship("SourceSnapshot", back_populates="source_object")
    connector_credential = relationship("ConnectorCredential")
