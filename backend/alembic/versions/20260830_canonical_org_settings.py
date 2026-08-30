"""Migrate organization settings to canonical keys.

Revision ID: c4b7e97a1d53
Revises: 7f31c4d02e8a
"""

import json
from datetime import datetime, timedelta
from typing import Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from alembic import op

revision: str = "c4b7e97a1d53"
down_revision: str | None = "7f31c4d02e8a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULTS: dict[str, object] = {
    "work_start_time": "09:00",
    "work_end_time": "17:00",
    "late_threshold_minutes": 15,
    "require_liveness": True,
    "liveness_threshold": 0.80,
    "face_match_threshold": 0.75,
}


def derived_start_time(settings: dict[str, object]) -> str:
    legacy_end = settings.get("check_in_end")
    if not isinstance(legacy_end, str):
        return "09:00"
    try:
        parsed = datetime.strptime(legacy_end, "%H:%M")
    except ValueError:
        return "09:00"
    grace = settings.get("late_threshold_minutes", 15)
    if not isinstance(grace, int) or isinstance(grace, bool):
        grace = 15
    return (parsed - timedelta(minutes=grace)).strftime("%H:%M")


def valid_non_utc_timezone(value: object) -> str | None:
    if not isinstance(value, str) or value == "UTC":
        return None
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return None
    return value


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, timezone, settings FROM orgs")).mappings()
    for row in rows:
        stored = dict(row["settings"] or {})
        if "work_start_time" not in stored:
            stored["work_start_time"] = derived_start_time(stored)
        if "face_match_threshold" not in stored:
            stored["face_match_threshold"] = stored.get(
                "recognition_threshold",
                DEFAULTS["face_match_threshold"],
            )
        for key, value in DEFAULTS.items():
            stored.setdefault(key, value)

        new_timezone = row["timezone"]
        if new_timezone == "UTC":
            migrated_timezone = valid_non_utc_timezone(stored.get("timezone"))
            if migrated_timezone is not None:
                new_timezone = migrated_timezone

        connection.execute(
            sa.text(
                "UPDATE orgs "
                "SET settings = CAST(:settings AS jsonb), timezone = :timezone "
                "WHERE id = :org_id"
            ),
            {
                "settings": json.dumps(stored, separators=(",", ":")),
                "timezone": new_timezone,
                "org_id": row["id"],
            },
        )


def downgrade() -> None:
    # Legacy keys are retained for immediate application rollback.
    pass
