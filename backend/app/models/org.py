import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .attendance_log import AttendanceLog
    from .audit_log import AuditLog
    from .calendar_exception import CalendarException
    from .device import Device
    from .organizational_unit import OrganizationalUnit
    from .shift import Shift
    from .shift_assignment import UserShiftAssignment
    from .unit_assignment import UserUnitAssignment
    from .user import User


class Org(Base, TimestampMixin):
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    settings: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="org", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="org", cascade="all, delete-orphan"
    )
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        "AttendanceLog", back_populates="org"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="org")
    organizational_units: Mapped[list["OrganizationalUnit"]] = relationship(
        "OrganizationalUnit", back_populates="org", cascade="all, delete-orphan"
    )
    unit_assignments: Mapped[list["UserUnitAssignment"]] = relationship(
        "UserUnitAssignment", back_populates="org", cascade="all, delete-orphan"
    )
    shifts: Mapped[list["Shift"]] = relationship(
        "Shift", back_populates="org", cascade="all, delete-orphan"
    )
    shift_assignments: Mapped[list["UserShiftAssignment"]] = relationship(
        "UserShiftAssignment", back_populates="org", cascade="all, delete-orphan"
    )
    calendar_exceptions: Mapped[list["CalendarException"]] = relationship(
        "CalendarException", back_populates="org", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("orgs_slug_idx", "slug", unique=True),)
