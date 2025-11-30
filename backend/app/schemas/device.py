from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    """Schema for creating a new device."""
    
    name: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    device_type: str = Field(default="kiosk", pattern="^(kiosk|tablet|mobile|web)$")
    settings: Optional[dict] = Field(default_factory=dict)


class DeviceCreateResponse(BaseModel):
    """Schema for device creation response with secret."""
    
    id: UUID
    name: str
    device_secret: str  # Only returned on creation
    org_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceUpdate(BaseModel):
    """Schema for updating a device."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    device_type: Optional[str] = Field(None, pattern="^(kiosk|tablet|mobile|web)$")
    is_active: Optional[bool] = None
    settings: Optional[dict] = None


class DeviceResponse(BaseModel):
    """Schema for device response."""
    
    id: UUID
    org_id: UUID
    name: str
    location: Optional[str]
    device_type: str
    is_active: bool
    last_seen_at: Optional[datetime]
    settings: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
