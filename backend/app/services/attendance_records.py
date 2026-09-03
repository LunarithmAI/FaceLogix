from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.models.attendance_log import AttendanceLog
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.scheduling import attendance_status, resolve_schedule_for_event


def effective_attendance_condition() -> ColumnElement[bool]:
    replacement = aliased(AttendanceLog)
    return ~exists(
        select(replacement.id).where(replacement.supersedes_id == AttendanceLog.id)
    )


async def correct_attendance_log(
    db: AsyncSession,
    *,
    original_id: UUID,
    org_id: UUID,
    actor: User,
    user: User,
    event_time: datetime,
    event_type: str,
    explicit_status: str | None,
    reason: str,
    timezone_name: str,
) -> AttendanceLog:
    original = await db.scalar(
        select(AttendanceLog)
        .where(AttendanceLog.id == original_id, AttendanceLog.org_id == org_id)
        .with_for_update()
    )
    if original is None:
        raise HTTPException(status_code=404, detail="Attendance log not found")
    replacement_exists = await db.scalar(
        select(AttendanceLog.id).where(AttendanceLog.supersedes_id == original.id)
    )
    if replacement_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ATTENDANCE_CORRECTION_STALE",
                "message": "Only the current correction can be superseded",
            },
        )
    schedule = await resolve_schedule_for_event(
        db,
        org_id=org_id,
        timezone_name=timezone_name,
        user_id=user.id,
        event_time=event_time,
    )
    replacement = AttendanceLog(
        org_id=org_id,
        user_id=user.id,
        device_id=None,
        unit_id=schedule.unit_id,
        shift_id=schedule.shift_id,
        schedule_date=schedule.schedule_date,
        ts=event_time,
        type=event_type,
        status=explicit_status or attendance_status(event_type, event_time, schedule),
        confidence_score=None,
        meta={},
        source="manual",
        supersedes_id=original.id,
        correction_reason=reason.strip(),
        created_by_id=actor.id,
    )
    db.add(replacement)
    await db.flush()
    db.add(
        AuditLog(
            org_id=org_id,
            actor_id=actor.id,
            actor_type="user",
            action="attendance.correct",
            resource_type="attendance_log",
            resource_id=replacement.id,
            changes={
                "supersedes_id": str(original.id),
                "user_id": str(user.id),
                "event_time": event_time.isoformat(),
                "type": event_type,
                "status": replacement.status,
                "reason": reason.strip(),
            },
        )
    )
    return replacement
