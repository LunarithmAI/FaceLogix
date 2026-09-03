import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .org import Org
    from .organizational_unit import OrganizationalUnit
    from .user import User


class UserUnitAssignment(Base, TimestampMixin):
    __tablename__ = "user_unit_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizational_units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    org: Mapped["Org"] = relationship("Org", back_populates="unit_assignments")
    user: Mapped["User"] = relationship("User", back_populates="unit_assignments")
    unit: Mapped["OrganizationalUnit"] = relationship(
        "OrganizationalUnit", back_populates="assignments"
    )

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="user_unit_assignments_date_check",
        ),
        ExcludeConstraint(
            ("org_id", "="),
            ("user_id", "="),
            (func.daterange(effective_from, effective_to, "[]"), "&&"),
            using="gist",
            name="user_unit_assignments_no_overlap",
        ),
        Index(
            "user_unit_assignments_user_dates_idx",
            "user_id",
            "effective_from",
            "effective_to",
        ),
        Index("user_unit_assignments_unit_dates_idx", "unit_id", "effective_from", "effective_to"),
    )
