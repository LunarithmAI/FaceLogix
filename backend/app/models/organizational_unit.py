import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .org import Org
    from .unit_assignment import UserUnitAssignment
    from .user import User


class OrganizationalUnit(Base, TimestampMixin):
    __tablename__ = "organizational_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    org: Mapped["Org"] = relationship("Org", back_populates="organizational_units")
    assignments: Mapped[list["UserUnitAssignment"]] = relationship(
        "UserUnitAssignment", back_populates="unit"
    )
    manager_scopes: Mapped[list["ManagerUnitScope"]] = relationship(
        "ManagerUnitScope", back_populates="unit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("kind IN ('class', 'department')", name="organizational_units_kind_check"),
        Index("organizational_units_org_idx", "org_id"),
        Index(
            "organizational_units_org_name_unique",
            "org_id",
            func.lower(func.btrim(name)),
            unique=True,
        ),
    )


class ManagerUnitScope(Base):
    __tablename__ = "manager_unit_scopes"

    manager_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizational_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    manager: Mapped["User"] = relationship("User", back_populates="managed_unit_scopes")
    unit: Mapped["OrganizationalUnit"] = relationship(
        "OrganizationalUnit", back_populates="manager_scopes"
    )

