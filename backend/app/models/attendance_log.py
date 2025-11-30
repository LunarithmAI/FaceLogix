import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .device import Device
    from .org import Org
    from .user import User


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    org: Mapped["Org"] = relationship("Org", back_populates="attendance_logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="attendance_logs")
    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="attendance_logs")

    __table_args__ = (
        Index("attendance_logs_org_user_ts_idx", "org_id", "user_id", ts.desc()),
        Index("attendance_logs_device_ts_idx", "device_id", ts.desc()),
        Index("attendance_logs_ts_idx", ts.desc()),
        Index("attendance_logs_org_status_idx", "org_id", "status"),
    )
