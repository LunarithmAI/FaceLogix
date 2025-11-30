import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .attendance_log import AttendanceLog
    from .org import Org


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_type: Mapped[str] = mapped_column(String(50), default="kiosk", nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    org: Mapped["Org"] = relationship("Org", back_populates="devices")
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        "AttendanceLog",
        back_populates="device"
    )

    __table_args__ = (
        Index("devices_org_id_idx", "org_id"),
        Index("devices_org_active_idx", "org_id", "is_active", postgresql_where="is_active = TRUE"),
    )
