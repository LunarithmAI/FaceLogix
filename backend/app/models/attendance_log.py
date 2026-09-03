import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .device import Device
    from .org import Org
    from .organizational_unit import OrganizationalUnit
    from .shift import Shift
    from .user import User


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizational_units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="RESTRICT"), nullable=True
    )
    schedule_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    meta: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="face", server_default="face"
    )
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_logs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    correction_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    org: Mapped["Org"] = relationship("Org", back_populates="attendance_logs")
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="attendance_logs", foreign_keys=[user_id]
    )
    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="attendance_logs")
    unit: Mapped[Optional["OrganizationalUnit"]] = relationship("OrganizationalUnit")
    shift: Mapped[Optional["Shift"]] = relationship("Shift")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    supersedes: Mapped[Optional["AttendanceLog"]] = relationship(
        "AttendanceLog", remote_side=[id]
    )

    __table_args__ = (
        Index("attendance_logs_org_user_ts_idx", "org_id", "user_id", ts.desc()),
        Index("attendance_logs_device_ts_idx", "device_id", ts.desc()),
        Index("attendance_logs_ts_idx", ts.desc()),
        Index("attendance_logs_org_status_idx", "org_id", "status"),
        CheckConstraint("source IN ('face', 'manual')", name="attendance_logs_source_check"),
        UniqueConstraint("supersedes_id", name="attendance_logs_supersedes_unique"),
        Index("attendance_logs_org_schedule_idx", "org_id", "schedule_date"),
        Index("attendance_logs_unit_schedule_idx", "unit_id", "schedule_date"),
        Index("attendance_logs_shift_schedule_idx", "shift_id", "schedule_date"),
    )
