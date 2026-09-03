#!/usr/bin/env python3
"""Reconcile attendance data written while an older application image was active."""

import asyncio
import hashlib
import json
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _local_date(value: datetime, timezone_name: str) -> date:
    return _aware(value).astimezone(ZoneInfo(timezone_name)).date()


def _parse_time(value: object, fallback: str) -> time:
    if isinstance(value, str):
        try:
            return time.fromisoformat(value)
        except ValueError:
            pass
    return time.fromisoformat(fallback)


def _fingerprint(settings: dict[str, object]) -> str:
    legacy = {
        "work_start_time": settings.get("work_start_time", "09:00"),
        "work_end_time": settings.get("work_end_time", "17:00"),
        "late_threshold_minutes": settings.get("late_threshold_minutes", 15),
    }
    encoded = json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


async def _replace_assignment(
    db: AsyncSession,
    *,
    table: str,
    target_column: str,
    org_id: UUID,
    user_id: UUID,
    target_id: UUID,
    effective_from: date,
) -> None:
    rows = list(
        (
            await db.execute(
                text(
                    f"SELECT id, {target_column} AS target_id, effective_from, effective_to "
                    f"FROM {table} WHERE org_id = :org_id AND user_id = :user_id "
                    "ORDER BY effective_from FOR UPDATE"
                ),
                {"org_id": org_id, "user_id": user_id},
            )
        ).mappings()
    )
    containing = next(
        (
            row
            for row in rows
            if row["effective_from"] <= effective_from
            and (row["effective_to"] is None or row["effective_to"] >= effective_from)
        ),
        None,
    )
    if containing is not None and containing["target_id"] == target_id:
        return
    next_row = next((row for row in rows if row["effective_from"] > effective_from), None)
    replacement_end = (
        next_row["effective_from"] - timedelta(days=1) if next_row is not None else None
    )
    if containing is not None:
        old_end = containing["effective_to"]
        if containing["effective_from"] == effective_from:
            await db.execute(
                text(
                    f"UPDATE {table} SET {target_column} = :target_id, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"id": containing["id"], "target_id": target_id},
            )
            return
        await db.execute(
            text(
                f"UPDATE {table} SET effective_to = :end, updated_at = now() WHERE id = :id"
            ),
            {"id": containing["id"], "end": effective_from - timedelta(days=1)},
        )
        replacement_end = old_end
    await db.execute(
        text(
            f"INSERT INTO {table} "
            f"(id, org_id, user_id, {target_column}, effective_from, effective_to) "
            "VALUES (:id, :org_id, :user_id, :target_id, :effective_from, :effective_to)"
        ),
        {
            "id": uuid4(),
            "org_id": org_id,
            "user_id": user_id,
            "target_id": target_id,
            "effective_from": effective_from,
            "effective_to": replacement_end,
        },
    )


async def _unit_for_name(db: AsyncSession, org_id: UUID, name: str) -> UUID:
    existing = await db.scalar(
        text(
            "SELECT id FROM organizational_units "
            "WHERE org_id = :org_id AND lower(btrim(name)) = lower(btrim(:name))"
        ),
        {"org_id": org_id, "name": name},
    )
    if existing is not None:
        return existing
    unit_id = uuid4()
    await db.execute(
        text(
            "INSERT INTO organizational_units (id, org_id, name, kind) "
            "VALUES (:id, :org_id, :name, 'department')"
        ),
        {"id": unit_id, "org_id": org_id, "name": name.strip()},
    )
    return unit_id


async def _reconcile_org(db: AsyncSession, org: dict[str, Any]) -> None:
    org_id = org["id"]
    timezone_name = org["timezone"]
    settings = dict(org["settings"] or {})
    users = list(
        (
            await db.execute(
                text(
                    "SELECT id, department, is_active, created_at, updated_at FROM users "
                    "WHERE org_id = :org_id ORDER BY id FOR UPDATE"
                ),
                {"org_id": org_id},
            )
        ).mappings()
    )

    for user in users:
        department = user["department"]
        if not isinstance(department, str) or not department.strip():
            continue
        unit_id = await _unit_for_name(db, org_id, department)
        assignment_date = _local_date(user["updated_at"] or user["created_at"], timezone_name)
        await _replace_assignment(
            db,
            table="user_unit_assignments",
            target_column="unit_id",
            org_id=org_id,
            user_id=user["id"],
            target_id=unit_id,
            effective_from=assignment_date,
        )

    current_fingerprint = _fingerprint(settings)
    stored_fingerprint = settings.get("_legacy_schedule_fingerprint")
    default_shift_id = await db.scalar(
        text(
            "SELECT id FROM shifts WHERE org_id = :org_id "
            "ORDER BY created_at DESC, id DESC LIMIT 1"
        ),
        {"org_id": org_id},
    )
    if stored_fingerprint != current_fingerprint:
        start = _parse_time(settings.get("work_start_time"), "09:00")
        end = _parse_time(settings.get("work_end_time"), "17:00")
        if start == end:
            raise RuntimeError(f"Cannot recover zero-duration schedule for organization {org_id}")
        grace = settings.get("late_threshold_minutes", 15)
        if not isinstance(grace, int) or isinstance(grace, bool):
            grace = 15
        updated_at = _aware(org["updated_at"])
        shift_name = (
            "Recovered shift "
            f"{updated_at.astimezone(ZoneInfo(timezone_name)):%Y-%m-%d %H:%M:%S}"
        )
        default_shift_id = await db.scalar(
            text(
                "SELECT id FROM shifts WHERE org_id = :org_id "
                "AND lower(btrim(name)) = lower(btrim(:name))"
            ),
            {"org_id": org_id, "name": shift_name},
        )
        if default_shift_id is None:
            default_shift_id = uuid4()
            await db.execute(
                text(
                    "INSERT INTO shifts (id, org_id, name, start_time, end_time, "
                    "late_grace_minutes, early_departure_grace_minutes, scheduled_weekdays) "
                    "VALUES (:id, :org_id, :name, :start, :end, :grace, 0, "
                    "ARRAY[0,1,2,3,4]::integer[])"
                ),
                {
                    "id": default_shift_id,
                    "org_id": org_id,
                    "name": shift_name,
                    "start": start,
                    "end": end,
                    "grace": max(0, grace),
                },
            )
        effective_from = _local_date(updated_at, timezone_name)
        for user in users:
            if user["is_active"]:
                await _replace_assignment(
                    db,
                    table="user_shift_assignments",
                    target_column="shift_id",
                    org_id=org_id,
                    user_id=user["id"],
                    target_id=default_shift_id,
                    effective_from=effective_from,
                )
        settings["_legacy_schedule_fingerprint"] = current_fingerprint
        await db.execute(
            text("UPDATE orgs SET settings = CAST(:settings AS jsonb) WHERE id = :org_id"),
            {
                "org_id": org_id,
                "settings": json.dumps(settings, separators=(",", ":")),
            },
        )

    if default_shift_id is not None:
        for user in users:
            has_shift = await db.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM user_shift_assignments "
                    "WHERE org_id = :org_id AND user_id = :user_id)"
                ),
                {"org_id": org_id, "user_id": user["id"]},
            )
            if not has_shift:
                await _replace_assignment(
                    db,
                    table="user_shift_assignments",
                    target_column="shift_id",
                    org_id=org_id,
                    user_id=user["id"],
                    target_id=default_shift_id,
                    effective_from=_local_date(user["created_at"], timezone_name),
                )

    logs = list(
        (
            await db.execute(
                text(
                    "SELECT id, user_id, ts, type, status FROM attendance_logs "
                    "WHERE org_id = :org_id AND "
                    "(unit_id IS NULL OR shift_id IS NULL OR schedule_date IS NULL "
                    "OR (type = 'check_out' AND status IN ('on_time', 'early'))) "
                    "ORDER BY ts, id FOR UPDATE"
                ),
                {"org_id": org_id},
            )
        ).mappings()
    )
    for log in logs:
        local = _aware(log["ts"]).astimezone(ZoneInfo(timezone_name))
        schedule_date = local.date()
        unit_id = None
        shift_id = None
        shift_start = None
        shift_end = None
        if log["user_id"] is not None:
            unit_id = await db.scalar(
                text(
                    "SELECT unit_id FROM user_unit_assignments WHERE user_id = :user_id "
                    "AND effective_from <= :event_date "
                    "AND (effective_to IS NULL OR effective_to >= :event_date) "
                    "ORDER BY effective_from DESC LIMIT 1"
                ),
                {"user_id": log["user_id"], "event_date": local.date()},
            )
            shift_row = (
                await db.execute(
                    text(
                        "SELECT s.id, s.start_time, s.end_time FROM user_shift_assignments a "
                        "JOIN shifts s ON s.id = a.shift_id WHERE a.user_id = :user_id "
                        "AND a.effective_from <= :event_date "
                        "AND (a.effective_to IS NULL OR a.effective_to >= :event_date) "
                        "ORDER BY a.effective_from DESC LIMIT 1"
                    ),
                    {"user_id": log["user_id"], "event_date": local.date()},
                )
            ).mappings().first()
            if shift_row is not None:
                shift_id = shift_row["id"]
                shift_start = shift_row["start_time"]
                shift_end = shift_row["end_time"]
                if shift_end < shift_start and local.timetz().replace(tzinfo=None) <= shift_end:
                    previous_date = local.date() - timedelta(days=1)
                    previous_shift = (
                        await db.execute(
                            text(
                                "SELECT s.id, s.start_time, s.end_time "
                                "FROM user_shift_assignments a JOIN shifts s ON s.id = a.shift_id "
                                "WHERE a.user_id = :user_id AND a.effective_from <= :event_date "
                                "AND (a.effective_to IS NULL OR a.effective_to >= :event_date) "
                                "ORDER BY a.effective_from DESC LIMIT 1"
                            ),
                            {"user_id": log["user_id"], "event_date": previous_date},
                        )
                    ).mappings().first()
                    if (
                        previous_shift is not None
                        and previous_shift["end_time"] < previous_shift["start_time"]
                        and local.timetz().replace(tzinfo=None) <= previous_shift["end_time"]
                    ):
                        schedule_date = previous_date
                        shift_id = previous_shift["id"]
        status = log["status"]
        if log["type"] == "check_out" and status == "on_time":
            status = "complete"
        elif log["type"] == "check_out" and status == "early":
            status = "left_early"
        await db.execute(
            text(
                "UPDATE attendance_logs SET unit_id = COALESCE(unit_id, :unit_id), "
                "shift_id = COALESCE(shift_id, :shift_id), "
                "schedule_date = COALESCE(schedule_date, :schedule_date), "
                "source = COALESCE(source, 'face'), status = :status WHERE id = :id"
            ),
            {
                "id": log["id"],
                "unit_id": unit_id,
                "shift_id": shift_id,
                "schedule_date": schedule_date,
                "status": status,
            },
        )


async def reconcile_legacy_attendance() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        orgs = list(
            (
                await db.execute(
                    text(
                        "SELECT id, timezone, settings, updated_at FROM orgs "
                        "ORDER BY id FOR UPDATE"
                    )
                )
            ).mappings()
        )
        for org in orgs:
            await _reconcile_org(db, dict(org))


if __name__ == "__main__":
    asyncio.run(reconcile_legacy_attendance())
