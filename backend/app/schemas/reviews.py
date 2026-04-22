from uuid import UUID

from pydantic import BaseModel, Field


class ManualReviewRequest(BaseModel):
    title: str
    text: str = Field(min_length=1)
    max_iterations: int = Field(default=3, ge=1, le=10)
    publish_mode: str = "internal_only"


class ReviewRunResponse(BaseModel):
    session_id: UUID
    status: str
    queued: bool
