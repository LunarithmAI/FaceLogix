import re
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class OrgSettingsData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    work_start_time: str = "09:00"
    work_end_time: str = "17:00"
    late_threshold_minutes: int = Field(default=15, ge=0, le=120)
    require_liveness: bool = True
    liveness_threshold: float = Field(default=0.80, ge=0.50, le=0.99)
    face_match_threshold: float = Field(default=0.75, ge=0.30, le=0.95)

    @field_validator("work_start_time", "work_end_time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        if not TIME_PATTERN.fullmatch(value):
            raise ValueError("time must use HH:MM")
        return value


class OrgSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_start_time: str | None = None
    work_end_time: str | None = None
    late_threshold_minutes: int | None = Field(default=None, ge=0, le=120)
    require_liveness: bool | None = None
    liveness_threshold: float | None = Field(default=None, ge=0.50, le=0.99)
    face_match_threshold: float | None = Field(default=None, ge=0.30, le=0.95)

    @field_validator("work_start_time", "work_end_time")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        if value is not None and not TIME_PATTERN.fullmatch(value):
            raise ValueError("time must use HH:MM")
        return value


class OrgSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    timezone: str
    is_active: bool
    settings: OrgSettingsData
    created_at: datetime
    updated_at: datetime


class OrgSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, max_length=50)
    settings: OrgSettingsPatch | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return value


class SystemInfoResponse(BaseModel):
    version: str
    environment: str
    face_service_status: str
    database_status: str
    total_users: int
    total_devices: int
    uptime_hours: float


class FaceServiceTestResponse(BaseModel):
    status: str
    latency_ms: float


def canonical_org_settings(raw: dict[str, object] | None) -> OrgSettingsData:
    return OrgSettingsData.model_validate(raw or {})
