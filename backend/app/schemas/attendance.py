from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: str = Field(min_length=1)


class CheckInResponse(BaseModel):
    success: bool
    status: str
    message: str
    user_id: UUID | None = None
    user_name: str | None = None
    event_time: datetime | None = None
    schedule_date: date | None = None
    unit_id: UUID | None = None
    shift_id: UUID | None = None
    confidence_score: float | None = None


class AttendanceLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    user_name: str | None = None
    device_id: UUID | None
    device_name: str | None = None
    unit_id: UUID | None
    unit_name: str | None = None
    shift_id: UUID | None
    shift_name: str | None = None
    schedule_date: date | None
    event_time: datetime
    type: str
    status: str
    source: str
    confidence_score: float | None
    supersedes_id: UUID | None
    correction_reason: str | None
    created_by_id: UUID | None


class AttendanceCorrectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID | None = None
    event_time: datetime
    type: Literal["check_in", "check_out"]
    status: Literal["on_time", "late", "early_departure", "unscheduled"] | None = None
    reason: str = Field(min_length=3, max_length=1000)



    @field_validator("event_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_time must include a timezone offset")
        return value
class DailyAttendanceUser(BaseModel):
    user_id: UUID
    user_name: str
    unit_id: UUID | None
    unit_name: str | None
    shift_id: UUID | None
    shift_name: str | None
    scheduled: bool
    check_in: AttendanceLogResponse | None
    check_out: AttendanceLogResponse | None
    status: str


class DailyAttendanceResponse(BaseModel):
    date: date
    scheduled: int
    present: int
    absent: int
    users: list[DailyAttendanceUser]
    unknown_attempts: int
    ambiguous_attempts: int


class DailySummary(BaseModel):
    date: date
    scheduled: int
    checked_in: int
    on_time: int
    late: int
    absent: int
    unknown_attempts: int
    ambiguous_attempts: int
