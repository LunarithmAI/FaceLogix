"""add device credential version

Revision ID: 7f31c4d02e8a
Revises: bb0f836b8a6a
Create Date: 2026-08-30 00:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7f31c4d02e8a"
down_revision: str | None = "bb0f836b8a6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("token_version", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("devices", "token_version")
