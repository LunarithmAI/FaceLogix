from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CalendarExceptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: UUID | None = None
    exception_date: date
    kind: Literal["holiday", "working_day"]
    name: str = Field(min_length=1, max_length=255)


class CalendarExceptionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: UUID | None = None
    exception_date: date | None = None
    kind: Literal["holiday", "working_day"] | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)


class CalendarExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    unit_id: UUID | None
    exception_date: date
    kind: Literal["holiday", "working_day"]
    name: str
    created_at: datetime
    updated_at: datetime
