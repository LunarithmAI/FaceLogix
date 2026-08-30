from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class AuthenticatedIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject_id: UUID
    org_id: UUID
    kind: Literal["user", "device"]
    role: UserRole | None = None
