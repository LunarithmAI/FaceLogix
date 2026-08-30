from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    device_type: str = Field(default="kiosk", pattern="^(kiosk|tablet|mobile|web)$")
    settings: dict[str, object] | None = Field(default_factory=dict)


class DeviceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    device_type: str | None = Field(None, pattern="^(kiosk|tablet|mobile|web)$")
    is_active: bool | None = None
    settings: dict[str, object] | None = None


class DeviceResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    location: str | None
    device_type: str
    is_active: bool
    last_seen_at: datetime | None
    settings: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceCreateResponse(DeviceResponse):
    device_secret: str
