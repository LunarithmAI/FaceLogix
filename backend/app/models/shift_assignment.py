import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .org import Org
    from .shift import Shift
    from .user import User


class UserShiftAssignment(Base, TimestampMixin):
    __tablename__ = "user_shift_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="RESTRICT"), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    org: Mapped["Org"] = relationship("Org", back_populates="shift_assignments")
    user: Mapped["User"] = relationship("User", back_populates="shift_assignments")
    shift: Mapped["Shift"] = relationship("Shift", back_populates="assignments")

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="user_shift_assignments_date_check",
        ),
        ExcludeConstraint(
            ("org_id", "="),
            ("user_id", "="),
            (func.daterange(effective_from, effective_to, "[]"), "&&"),
            using="gist",
            name="user_shift_assignments_no_overlap",
        ),
        Index(
            "user_shift_assignments_user_dates_idx", "user_id", "effective_from", "effective_to"
        ),
        Index(
            "user_shift_assignments_shift_dates_idx", "shift_id", "effective_from", "effective_to"
        ),
    )
