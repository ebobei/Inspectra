from uuid import UUID

from pydantic import BaseModel


class WebhookAcceptedResponse(BaseModel):
    accepted: bool = True
    queued: bool = False
    trigger_type: str = "webhook"
    session_id: UUID | None = None
    reason: str | None = None
