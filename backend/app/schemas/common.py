from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class APIMessage(BaseModel):
    message: str


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EntityTimestamps(BaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime
