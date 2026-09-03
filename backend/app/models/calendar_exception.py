import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .org import Org
    from .organizational_unit import OrganizationalUnit


class CalendarException(Base, TimestampMixin):
    __tablename__ = "calendar_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizational_units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    org: Mapped["Org"] = relationship("Org", back_populates="calendar_exceptions")
    unit: Mapped["OrganizationalUnit | None"] = relationship("OrganizationalUnit")

    __table_args__ = (
        CheckConstraint(
            "kind IN ('holiday', 'working_day')", name="calendar_exceptions_kind_check"
        ),
        Index(
            "calendar_exceptions_org_date_unique",
            "org_id",
            "exception_date",
            unique=True,
            postgresql_where=text("unit_id IS NULL"),
        ),
        Index(
            "calendar_exceptions_unit_date_unique",
            "org_id",
            "unit_id",
            "exception_date",
            unique=True,
            postgresql_where=text("unit_id IS NOT NULL"),
        ),
        Index("calendar_exceptions_org_range_idx", "org_id", "exception_date"),
    )
