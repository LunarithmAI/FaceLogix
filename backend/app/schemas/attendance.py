from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: str = Field(min_length=1)
    device_id: UUID | None = None
    timestamp: datetime | None = None


class CheckInResponse(BaseModel):
    """Schema for check-in/check-out response."""

    success: bool
    status: str  # "on_time", "late", "unknown_user", "already_checked_in", "no_face_detected"
    message: str
    user_id: UUID | None = None
    user_name: str | None = None
    check_in_time: datetime | None = None
    confidence_score: float | None = None


class AttendanceLogResponse(BaseModel):
    """Schema for attendance log response."""

    id: UUID
    user_id: UUID | None
    user_name: str | None = None
    device_id: UUID | None
    device_name: str | None = None
    ts: datetime
    type: str  # "check_in", "check_out"
    status: str  # "on_time", "late", "early", "unknown_user"
    confidence_score: float | None

    model_config = ConfigDict(from_attributes=True)


class DailySummary(BaseModel):
    """Schema for daily attendance summary."""

    date: date
    total_users: int
    checked_in: int
    on_time: int
    late: int
    absent: int
    unknown_attempts: int
