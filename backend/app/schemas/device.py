from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeviceSettingsData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    allow_check_in: bool = True
    allow_check_out: bool = True
    default_mode: Literal["check_in", "check_out"] = "check_in"
    camera_facing: Literal["user", "environment"] = "user"

    @model_validator(mode="after")
    def validate_default_mode(self) -> "DeviceSettingsData":
        if self.allow_check_in or self.allow_check_out:
            enabled = self.allow_check_in if self.default_mode == "check_in" else self.allow_check_out
            if not enabled:
                raise ValueError("default mode must select an enabled action")
        return self


class DeviceSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_check_in: bool | None = None
    allow_check_out: bool | None = None
    default_mode: Literal["check_in", "check_out"] | None = None
    camera_facing: Literal["user", "environment"] | None = None


class DeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    device_type: str = Field(default="kiosk", pattern="^(kiosk|tablet|mobile|web)$")
    settings: DeviceSettingsData = Field(default_factory=DeviceSettingsData)


class DeviceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    device_type: str | None = Field(None, pattern="^(kiosk|tablet|mobile|web)$")
    is_active: bool | None = None


class DeviceResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    location: str | None
    device_type: str
    is_active: bool
    last_seen_at: datetime | None
    settings: DeviceSettingsData
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceCreateResponse(DeviceResponse):
    device_secret: str


def canonical_device_settings(raw: dict[str, object] | None) -> DeviceSettingsData:
    return DeviceSettingsData.model_validate(raw or {})
