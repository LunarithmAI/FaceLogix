from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

UnitKind = Literal["class", "department"]


class UnitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: UnitKind
    is_active: bool


class UnitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    kind: UnitKind

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()


class UnitPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    kind: UnitKind | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class UnitResponse(UnitSummary):
    org_id: UUID
    created_at: datetime
    updated_at: datetime


class ManagedUnitsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_ids: list[UUID] = Field(default_factory=list, max_length=100)

    @field_validator("unit_ids")
    @classmethod
    def distinct_unit_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("unit IDs must be distinct")
        return value


class UnitAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: UUID | None
    effective_from: date


class UnitAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    unit: UnitSummary
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime
