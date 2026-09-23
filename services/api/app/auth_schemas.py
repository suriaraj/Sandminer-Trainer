from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    session_id: UUID


class SessionResponse(BaseModel):
    id: UUID
    device_label: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked: bool
