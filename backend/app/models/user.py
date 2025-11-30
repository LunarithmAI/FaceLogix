import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .attendance_log import AttendanceLog
    from .face_embedding import FaceEmbedding
    from .org import Org
    from .refresh_token import RefreshToken


class User(Base, TimestampMixin):
    __tablename__ = "users"

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
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enrolled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    org: Mapped["Org"] = relationship("Org", back_populates="users")
    face_embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        "FaceEmbedding",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        "AttendanceLog",
        back_populates="user"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("org_id", "email", name="users_email_org_unique"),
        UniqueConstraint("org_id", "external_id", name="users_external_id_org_unique"),
        Index("users_org_id_idx", "org_id"),
        Index("users_email_idx", "email"),
        Index("users_external_id_idx", "external_id"),
        Index("users_org_active_idx", "org_id", "is_active", postgresql_where="is_active = TRUE"),
    )
