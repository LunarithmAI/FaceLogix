from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ShiftSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    start_time: time
    end_time: time
    late_grace_minutes: int
    early_departure_grace_minutes: int
    scheduled_weekdays: list[int]
    is_active: bool


class ShiftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    start_time: time
    end_time: time
    late_grace_minutes: int = Field(default=0, ge=0, le=720)
    early_departure_grace_minutes: int = Field(default=0, ge=0, le=720)
    scheduled_weekdays: list[int] = Field(min_length=0, max_length=7)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("scheduled_weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)) or any(day < 0 or day > 6 for day in value):
            raise ValueError("weekdays must be distinct integers from 0 through 6")
        return sorted(value)

    @model_validator(mode="after")
    def reject_zero_duration(self) -> "ShiftCreate":
        if self.start_time == self.end_time:
            raise ValueError("shift start and end times must differ")
        return self


class ShiftPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    start_time: time | None = None
    end_time: time | None = None
    late_grace_minutes: int | None = Field(default=None, ge=0, le=720)
    early_departure_grace_minutes: int | None = Field(default=None, ge=0, le=720)
    scheduled_weekdays: list[int] | None = Field(default=None, max_length=7)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("scheduled_weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and (
            len(value) != len(set(value)) or any(day < 0 or day > 6 for day in value)
        ):
            raise ValueError("weekdays must be distinct integers from 0 through 6")
        return sorted(value) if value is not None else None


class ShiftResponse(ShiftSummary):
    org_id: UUID
    created_at: datetime
    updated_at: datetime


class ShiftAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shift_id: UUID | None
    effective_from: date


class ShiftAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    shift: ShiftSummary
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


class UnitShiftAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shift_id: UUID | None
    effective_from: date


class UnitShiftAssignmentResponse(BaseModel):
    unit_id: UUID
    shift_id: UUID | None
    effective_from: date
    users_updated: int
