"""add attendance operations domain

Revision ID: f3c9a71b4e02
Revises: d9e54861a72c
Create Date: 2026-09-03 00:00:00+00:00
"""

import hashlib
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f3c9a71b4e02"
down_revision: str | None = "d9e54861a72c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _parse_time(value: object, fallback: str) -> time:
    candidate = value if isinstance(value, str) else fallback
    try:
        return time.fromisoformat(candidate)
    except ValueError:
        return time.fromisoformat(fallback)


def _local_date(value: datetime, timezone_name: str) -> date:
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return aware.astimezone(ZoneInfo(timezone_name)).date()


def _schedule_date(value: datetime, timezone_name: str, start: time, end: time) -> date:
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    local = aware.astimezone(ZoneInfo(timezone_name))
    if end < start and local.timetz().replace(tzinfo=None) <= end:
        return local.date() - timedelta(days=1)
    return local.date()


def _fingerprint(settings: dict[str, object]) -> str:
    legacy = {
        "work_start_time": settings.get("work_start_time", "09:00"),
        "work_end_time": settings.get("work_end_time", "17:00"),
        "late_threshold_minutes": settings.get("late_threshold_minutes", 15),
    }
    payload = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def upgrade() -> None:
    connection = op.get_bind()
    org_rows = list(
        connection.execute(
            sa.text("SELECT id, timezone, settings, updated_at FROM orgs ORDER BY id")
        ).mappings()
    )
    invalid_org_ids = [
        str(row["id"])
        for row in org_rows
        if _parse_time(dict(row["settings"] or {}).get("work_start_time"), "09:00")
        == _parse_time(dict(row["settings"] or {}).get("work_end_time"), "17:00")
    ]
    if invalid_org_ids:
        raise RuntimeError(
            "Legacy work start and end times are equal for organization IDs: "
            + ", ".join(invalid_org_ids)
        )

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        "organizational_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('class', 'department')", name="organizational_units_kind_check"
        ),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("organizational_units_org_idx", "organizational_units", ["org_id"])
    op.execute(
        "CREATE UNIQUE INDEX organizational_units_org_name_unique "
        "ON organizational_units (org_id, lower(btrim(name)))"
    )

    op.create_table(
        "manager_unit_scopes",
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["organizational_units.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("manager_id", "unit_id"),
    )

    op.create_table(
        "shifts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("late_grace_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "early_departure_grace_minutes", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("scheduled_weekdays", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("start_time <> end_time", name="shifts_nonzero_duration_check"),
        sa.CheckConstraint(
            "late_grace_minutes >= 0 AND early_departure_grace_minutes >= 0",
            name="shifts_grace_nonnegative_check",
        ),
        sa.CheckConstraint(
            "scheduled_weekdays <@ ARRAY[0,1,2,3,4,5,6]::integer[] AND "
            + " AND ".join(
                f"cardinality(array_positions(scheduled_weekdays, {day})) <= 1"
                for day in range(7)
            ),
            name="shifts_weekdays_check",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("shifts_org_idx", "shifts", ["org_id"])
    op.execute(
        "CREATE UNIQUE INDEX shifts_org_name_unique ON shifts (org_id, lower(btrim(name)))"
    )

    for table_name, target_table, target_column in (
        ("user_unit_assignments", "organizational_units", "unit_id"),
        ("user_shift_assignments", "shifts", "shift_id"),
    ):
        op.create_table(
            table_name,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(target_column, postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.CheckConstraint(
                "effective_to IS NULL OR effective_to >= effective_from",
                name=f"{table_name}_date_check",
            ),
            sa.ForeignKeyConstraint(["org_id"], ["orgs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                [target_column], [f"{target_table}.id"], ondelete="RESTRICT"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.execute(
            f"ALTER TABLE {table_name} ADD CONSTRAINT {table_name}_no_overlap "
            "EXCLUDE USING gist (org_id WITH =, user_id WITH =, "
            "daterange(effective_from, effective_to, '[]') WITH &&)"
        )
        op.create_index(
            f"{table_name}_user_dates_idx",
            table_name,
            ["user_id", "effective_from", "effective_to"],
        )
        op.create_index(
            f"{table_name}_{target_column.removesuffix('_id')}_dates_idx",
            table_name,
            [target_column, "effective_from", "effective_to"],
        )

    op.create_table(
        "calendar_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('holiday', 'working_day')", name="calendar_exceptions_kind_check"
        ),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["organizational_units.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "calendar_exceptions_org_range_idx",
        "calendar_exceptions",
        ["org_id", "exception_date"],
    )
    op.create_index(
        "calendar_exceptions_org_date_unique",
        "calendar_exceptions",
        ["org_id", "exception_date"],
        unique=True,
        postgresql_where=sa.text("unit_id IS NULL"),
    )
    op.create_index(
        "calendar_exceptions_unit_date_unique",
        "calendar_exceptions",
        ["org_id", "unit_id", "exception_date"],
        unique=True,
        postgresql_where=sa.text("unit_id IS NOT NULL"),
    )

    op.add_column(
        "attendance_logs",
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "attendance_logs",
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("attendance_logs", sa.Column("schedule_date", sa.Date(), nullable=True))
    op.add_column(
        "attendance_logs",
        sa.Column("source", sa.String(length=32), server_default="face", nullable=False),
    )
    op.add_column(
        "attendance_logs",
        sa.Column("supersedes_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "attendance_logs", sa.Column("correction_reason", sa.String(length=1000), nullable=True)
    )
    op.add_column(
        "attendance_logs",
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_check_constraint(
        "attendance_logs_source_check", "attendance_logs", "source IN ('face', 'manual')"
    )
    op.create_foreign_key(
        "attendance_logs_unit_id_fkey",
        "attendance_logs",
        "organizational_units",
        ["unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "attendance_logs_shift_id_fkey",
        "attendance_logs",
        "shifts",
        ["shift_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "attendance_logs_supersedes_id_fkey",
        "attendance_logs",
        "attendance_logs",
        ["supersedes_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "attendance_logs_created_by_id_fkey",
        "attendance_logs",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "attendance_logs_supersedes_unique", "attendance_logs", ["supersedes_id"]
    )
    op.create_index(
        "attendance_logs_org_schedule_idx", "attendance_logs", ["org_id", "schedule_date"]
    )
    op.create_index(
        "attendance_logs_unit_schedule_idx", "attendance_logs", ["unit_id", "schedule_date"]
    )
    op.create_index(
        "attendance_logs_shift_schedule_idx", "attendance_logs", ["shift_id", "schedule_date"]
    )

    user_rows = list(
        connection.execute(
            sa.text(
                "SELECT id, org_id, department, role, created_at FROM users "
                "ORDER BY org_id, created_at, id"
            )
        ).mappings()
    )
    unit_ids: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
    user_unit_ids: dict[uuid.UUID, uuid.UUID] = {}
    for row in user_rows:
        raw_name = row["department"]
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        name = raw_name.strip()
        key = (row["org_id"], name.casefold())
        unit_id = unit_ids.get(key)
        if unit_id is None:
            unit_id = uuid.uuid4()
            unit_ids[key] = unit_id
            connection.execute(
                sa.text(
                    "INSERT INTO organizational_units (id, org_id, name, kind) "
                    "VALUES (:id, :org_id, :name, 'department')"
                ),
                {"id": unit_id, "org_id": row["org_id"], "name": name},
            )
        user_unit_ids[row["id"]] = unit_id
        timezone_name = next(
            org["timezone"] for org in org_rows if org["id"] == row["org_id"]
        )
        effective_from = _local_date(row["created_at"], timezone_name)
        connection.execute(
            sa.text(
                "INSERT INTO user_unit_assignments "
                "(id, org_id, user_id, unit_id, effective_from) "
                "VALUES (:id, :org_id, :user_id, :unit_id, :effective_from)"
            ),
            {
                "id": uuid.uuid4(),
                "org_id": row["org_id"],
                "user_id": row["id"],
                "unit_id": unit_id,
                "effective_from": effective_from,
            },
        )
        if row["role"] == "manager":
            connection.execute(
                sa.text(
                    "INSERT INTO manager_unit_scopes (manager_id, unit_id) "
                    "VALUES (:manager_id, :unit_id)"
                ),
                {"manager_id": row["id"], "unit_id": unit_id},
            )

    shift_ids: dict[uuid.UUID, uuid.UUID] = {}
    shift_times: dict[uuid.UUID, tuple[time, time]] = {}
    org_timezones: dict[uuid.UUID, str] = {}
    for org in org_rows:
        stored = dict(org["settings"] or {})
        start = _parse_time(stored.get("work_start_time"), "09:00")
        end = _parse_time(stored.get("work_end_time"), "17:00")
        grace = stored.get("late_threshold_minutes", 15)
        if not isinstance(grace, int) or isinstance(grace, bool):
            grace = 15
        shift_id = uuid.uuid4()
        shift_ids[org["id"]] = shift_id
        shift_times[org["id"]] = (start, end)
        org_timezones[org["id"]] = org["timezone"]
        connection.execute(
            sa.text(
                "INSERT INTO shifts (id, org_id, name, start_time, end_time, "
                "late_grace_minutes, early_departure_grace_minutes, scheduled_weekdays) "
                "VALUES (:id, :org_id, 'Default shift', :start, :end, :grace, 0, "
                "ARRAY[0,1,2,3,4]::integer[])"
            ),
            {
                "id": shift_id,
                "org_id": org["id"],
                "start": start,
                "end": end,
                "grace": max(0, grace),
            },
        )
        stored["_legacy_schedule_fingerprint"] = _fingerprint(stored)
        connection.execute(
            sa.text("UPDATE orgs SET settings = CAST(:settings AS jsonb) WHERE id = :id"),
            {
                "id": org["id"],
                "settings": json.dumps(stored, separators=(",", ":")),
            },
        )

    for user in user_rows:
        connection.execute(
            sa.text(
                "INSERT INTO user_shift_assignments "
                "(id, org_id, user_id, shift_id, effective_from) "
                "VALUES (:id, :org_id, :user_id, :shift_id, :effective_from)"
            ),
            {
                "id": uuid.uuid4(),
                "org_id": user["org_id"],
                "user_id": user["id"],
                "shift_id": shift_ids[user["org_id"]],
                "effective_from": _local_date(
                    user["created_at"], org_timezones[user["org_id"]]
                ),
            },
        )

    logs = list(
        connection.execute(
            sa.text("SELECT id, org_id, user_id, ts, type, status FROM attendance_logs")
        ).mappings()
    )
    for log in logs:
        start, end = shift_times[log["org_id"]]
        new_status = log["status"]
        if log["type"] == "check_out" and log["status"] == "on_time":
            new_status = "complete"
        elif log["type"] == "check_out" and log["status"] == "early":
            new_status = "left_early"
        connection.execute(
            sa.text(
                "UPDATE attendance_logs SET unit_id = :unit_id, shift_id = :shift_id, "
                "schedule_date = :schedule_date, source = 'face', status = :status "
                "WHERE id = :id"
            ),
            {
                "id": log["id"],
                "unit_id": user_unit_ids.get(log["user_id"]),
                "shift_id": shift_ids[log["org_id"]] if log["user_id"] else None,
                "schedule_date": _schedule_date(
                    log["ts"], org_timezones[log["org_id"]], start, end
                ),
                "status": new_status,
            },
        )


def downgrade() -> None:
    op.drop_index("attendance_logs_shift_schedule_idx", table_name="attendance_logs")
    op.drop_index("attendance_logs_unit_schedule_idx", table_name="attendance_logs")
    op.drop_index("attendance_logs_org_schedule_idx", table_name="attendance_logs")
    op.drop_constraint("attendance_logs_supersedes_unique", "attendance_logs", type_="unique")
    op.drop_constraint("attendance_logs_created_by_id_fkey", "attendance_logs", type_="foreignkey")
    op.drop_constraint("attendance_logs_supersedes_id_fkey", "attendance_logs", type_="foreignkey")
    op.drop_constraint("attendance_logs_shift_id_fkey", "attendance_logs", type_="foreignkey")
    op.drop_constraint("attendance_logs_unit_id_fkey", "attendance_logs", type_="foreignkey")
    op.drop_constraint("attendance_logs_source_check", "attendance_logs", type_="check")
    for column in (
        "created_by_id",
        "correction_reason",
        "supersedes_id",
        "source",
        "schedule_date",
        "shift_id",
        "unit_id",
    ):
        op.drop_column("attendance_logs", column)
    op.drop_table("calendar_exceptions")
    op.drop_table("user_shift_assignments")
    op.drop_table("user_unit_assignments")
    op.drop_table("shifts")
    op.drop_table("manager_unit_scopes")
    op.drop_table("organizational_units")
