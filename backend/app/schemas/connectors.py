from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorCreateRequest(BaseModel):
    connector_type: str
    name: str
    base_url: str
    auth_type: str = Field(default="bearer")
    secret_plain: str


class ConnectorResponse(BaseModel):
    id: UUID
    connector_type: str
    name: str
    base_url: str
    auth_type: str
    is_active: bool


class ConnectorTestResponse(BaseModel):
    ok: bool
    connector_type: str
    details: str
