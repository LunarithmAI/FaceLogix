"""align device token version default

Revision ID: d9e54861a72c
Revises: c4b7e97a1d53
Create Date: 2026-08-30 00:00:02+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9e54861a72c"
down_revision: str | None = "c4b7e97a1d53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "devices",
        "token_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "devices",
        "token_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
        server_default="1",
    )
