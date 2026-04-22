from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema


class PublicationResponse(BaseSchema):
    id: UUID
    review_session_id: UUID
    review_run_id: UUID
    target_system: str
    target_object_id: str
    external_comment_id: str | None
    publication_mode: str
    status: str
    published_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
