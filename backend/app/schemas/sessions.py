from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class SessionCreateRequest(BaseModel):
    source_type: str
    connector_id: UUID | None = None
    external_id: str
    external_url: str | None = None
    title: str | None = None
    max_iterations: int = Field(default=3, ge=1, le=10)
    recheck_enabled: bool = True


class SessionResponse(BaseSchema):
    id: UUID
    source_object_id: UUID
    status: str
    iteration_count: int
    max_iterations: int
    recheck_enabled: bool
    last_seen_input_hash: str | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime


class SessionListItem(BaseSchema):
    id: UUID
    source_object_id: UUID
    status: str
    iteration_count: int
    max_iterations: int
    updated_at: datetime


class SessionRunRequest(BaseModel):
    trigger_type: str = "manual"


class ReviewRunSummary(BaseSchema):
    id: UUID
    run_type: str
    status: str
    trigger_type: str
    llm_model: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class FindingSummary(BaseSchema):
    id: UUID
    finding_key: str
    category: str
    severity: str
    title: str
    description: str
    status: str
    times_repeated: int
    last_tone_level: str
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PublicationSummary(BaseSchema):
    id: UUID
    target_system: str
    target_object_id: str
    external_comment_id: str | None
    publication_mode: str
    status: str
    published_at: datetime | None
    created_at: datetime


class SessionDetailsResponse(SessionResponse):
    source_type: str
    external_system: str
    external_id: str
    external_url: str | None
    title: str | None
    connector_credential_id: UUID | None
    current_publication_id: UUID | None
    last_review_run_id: UUID | None
    open_findings_count: int
    resolved_findings_count: int
    runs: list[ReviewRunSummary]
    findings: list[FindingSummary]
    publications: list[PublicationSummary]
