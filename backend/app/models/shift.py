import uuid
from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .org import Org
    from .shift_assignment import UserShiftAssignment


class Shift(Base, TimestampMixin):
    __tablename__ = "shifts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    late_grace_minutes: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    early_departure_grace_minutes: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    scheduled_weekdays: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    org: Mapped["Org"] = relationship("Org", back_populates="shifts")
    assignments: Mapped[list["UserShiftAssignment"]] = relationship(
        "UserShiftAssignment", back_populates="shift"
    )

    __table_args__ = (
        CheckConstraint("start_time <> end_time", name="shifts_nonzero_duration_check"),
        CheckConstraint(
            "late_grace_minutes >= 0 AND early_departure_grace_minutes >= 0",
            name="shifts_grace_nonnegative_check",
        ),
        CheckConstraint(
            "scheduled_weekdays <@ ARRAY[0,1,2,3,4,5,6]::integer[] AND "
            + " AND ".join(
                f"cardinality(array_positions(scheduled_weekdays, {day})) <= 1"
                for day in range(7)
            ),
            name="shifts_weekdays_check",
        ),
        Index("shifts_org_idx", "org_id"),
        Index("shifts_org_name_unique", "org_id", func.lower(func.btrim(name)), unique=True),
    )
