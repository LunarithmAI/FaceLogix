from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.identity import UserRole
from app.schemas.shift import ShiftSummary
from app.schemas.unit import UnitSummary


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    external_id: str | None = Field(None, max_length=255)
    role: UserRole = UserRole.MEMBER
    unit_id: UUID | None = None
    shift_id: UUID | None = None


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Schema for updating a user."""

    email: EmailStr | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    external_id: str | None = Field(None, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    org_id: UUID
    email: str | None
    name: str
    external_id: str | None
    role: UserRole
    current_unit: UnitSummary | None
    current_shift: ShiftSummary | None
    managed_units: list[UnitSummary]
    is_active: bool
    enrolled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserEnrollResponse(BaseModel):
    """Schema for user enrollment response with face data."""

    user_id: UUID
    embeddings_count: int
    enrolled_at: datetime


class FaceStatusResponse(BaseModel):
    """Schema for face enrollment status response."""

    has_face: bool
    embeddings_count: int
    enrolled_at: datetime | None = None


class ResetPasswordRequest(BaseModel):
    """Schema for password reset request."""

    new_password: str = Field(..., min_length=8)


class UserActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: UUID
    shift_id: UUID | None = None


class FaceEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    images: list[str] = Field(min_length=1, max_length=5)


class UserImportError(BaseModel):
    row: int | None = Field(default=None, ge=2)
    code: str
    message: str
    field: str | None = None


class UserImportConflict(BaseModel):
    row: int = Field(ge=2)
    external_id: str
    email: str | None
    name: str
    existing_user_id: UUID
    existing_name: str
    allowed_actions: list[Literal["skip", "replace"]]


class UserImportPreviewResponse(BaseModel):
    package_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    total_rows: int = Field(ge=1, le=100)
    ready_count: int = Field(ge=0, le=100)
    conflict_count: int = Field(ge=0, le=100)
    error_count: int = Field(ge=0)
    conflicts: list[UserImportConflict]
    errors: list[UserImportError]


class UserImportResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int = Field(ge=2)
    action: Literal["skip", "replace"]


class UserImportCommitOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    resolutions: list[UserImportResolution] = Field(default_factory=list, max_length=100)


class UserImportResult(BaseModel):
    total_rows: int = Field(ge=1, le=100)
    created_count: int = Field(ge=0, le=100)
    replaced_count: int = Field(ge=0, le=100)
    skipped_count: int = Field(ge=0, le=100)
    embeddings_count: int = Field(ge=0, le=500)
