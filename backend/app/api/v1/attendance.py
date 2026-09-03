from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import (
    OPERATOR_ROLES,
    ensure_user_in_scope,
    get_current_identity,
    managed_unit_ids,
    require_device,
    require_operator,
)
from app.api.tenant import load_org, load_user
from app.core.database import get_db
from app.core.identity import AuthenticatedIdentity, UserRole
from app.core.images import ImagePayloadError, decode_image_payload
from app.core.time import local_day_bounds, utc_now
from app.models.attendance_log import AttendanceLog
from app.models.device import Device
from app.models.org import Org
from app.models.organizational_unit import OrganizationalUnit
from app.models.shift import Shift
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCorrectionCreate,
    AttendanceLogResponse,
    CheckInRequest,
    CheckInResponse,
    DailyAttendanceResponse,
    DailyAttendanceUser,
    DailySummary,
)
from app.schemas.common import PaginatedResponse
from app.schemas.device import canonical_device_settings
from app.schemas.settings import canonical_org_settings
from app.services.attendance_records import (
    correct_attendance_log,
    effective_attendance_condition,
)
from app.services.face_client import (
    FaceAnalysis,
    FaceServiceClient,
    FaceServiceError,
    get_face_client,
)
from app.services.face_identity import identify_face
from app.services.scheduling import (
    attendance_status,
    resolve_schedule_for_event,
    schedule_rows_for_date,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])

ATTENDANCE_FACE_STATUSES = {
    "INVALID_IMAGE": (
        "invalid_image",
        "The image could not be processed. Please try again.",
    ),
    "NO_FACE": (
        "no_face_detected",
        "No face was detected. Please position one face in the frame.",
    ),
    "MULTIPLE_FACES": (
        "multiple_faces",
        "Multiple faces were detected. Only one person may be in frame.",
    ),
    "LOW_QUALITY": (
        "low_quality",
        "Image quality is too low. Please improve lighting and try again.",
    ),
}


def face_failure_response(error: ImagePayloadError | FaceServiceError) -> CheckInResponse:
    mapped = ATTENDANCE_FACE_STATUSES.get(error.code)
    if mapped is not None:
        return CheckInResponse(success=False, status=mapped[0], message=mapped[1])
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


async def analyze_attendance_image(
    request: CheckInRequest,
    face_client: FaceServiceClient,
) -> FaceAnalysis | CheckInResponse:
    try:
        image_bytes = decode_image_payload(request.image)
        return await face_client.analyze(image_bytes)
    except (ImagePayloadError, FaceServiceError) as exc:
        return face_failure_response(exc)


async def lock_attendance_slot(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    schedule_date: date,
) -> None:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:slot, 0))"),
        {"slot": f"attendance:{org_id}:{user_id}:{schedule_date.isoformat()}"},
    )




async def process_attendance(
    event_type: str,
    request: CheckInRequest,
    db: AsyncSession,
    device: Device,
    face_client: FaceServiceClient,
) -> CheckInResponse:
    org = await load_org(db, device.org_id)
    policy = canonical_org_settings(org.settings)
    device_settings = canonical_device_settings(device.settings)
    action_enabled = (
        device_settings.allow_check_in
        if event_type == "check_in"
        else device_settings.allow_check_out
    )
    if not action_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "DEVICE_ACTION_DISABLED",
                "message": f"{event_type.replace('_', '-')} is disabled for this device",
            },
        )
    analysis = await analyze_attendance_image(request, face_client)
    if isinstance(analysis, CheckInResponse):
        return analysis
    event_time = utc_now()
    if policy.require_liveness and analysis.pad_live_score < policy.liveness_threshold:
        return CheckInResponse(
            success=False,
            status="spoof_detected",
            message="Liveness verification failed. Please try again in person.",
            event_time=event_time,
        )

    identity_match = await identify_face(
        db,
        org_id=org.id,
        embedding=analysis.embedding,
        threshold=policy.face_match_threshold,
    )
    if identity_match.status != "recognized" or identity_match.user_id is None:
        attempt_status = (
            "ambiguous_face"
            if identity_match.status == "ambiguous"
            else "unknown_user"
        )
        attempt_date = local_day_bounds(org.timezone, event_time)[0]
        db.add(
            AttendanceLog(
                org_id=org.id,
                device_id=device.id,
                schedule_date=attempt_date,
                ts=event_time,
                type=event_type,
                status=attempt_status,
                confidence_score=identity_match.score or analysis.quality_score,
                source="face",
            )
        )
        await db.commit()
        return CheckInResponse(
            success=False,
            status=attempt_status,
            message=(
                "Face matched multiple people. Please contact an administrator."
                if identity_match.status == "ambiguous"
                else "Face not recognized. Please contact an administrator."
            ),
            event_time=event_time,
            schedule_date=attempt_date,
            confidence_score=identity_match.score,
        )

    user = await load_user(db, org.id, identity_match.user_id)
    if not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = user.id
    user_name = user.name
    schedule = await resolve_schedule_for_event(
        db,
        org_id=org.id,
        timezone_name=org.timezone,
        user_id=user_id,
        event_time=event_time,
    )
    await lock_attendance_slot(
        db,
        org_id=org.id,
        user_id=user_id,
        schedule_date=schedule.schedule_date,
    )
    existing_types = set(
        (
            await db.scalars(
                select(AttendanceLog.type).where(
                    AttendanceLog.org_id == org.id,
                    AttendanceLog.user_id == user_id,
                    AttendanceLog.schedule_date == schedule.schedule_date,
                    AttendanceLog.status.notin_(["unknown_user", "ambiguous_face"]),
                    effective_attendance_condition(),
                )
            )
        ).all()
    )
    if event_type == "check_in" and "check_in" in existing_types:
        await db.rollback()
        return CheckInResponse(
            success=False,
            status="already_checked_in",
            message=f"You have already checked in for this shift, {user_name}.",
            user_id=user_id,
            user_name=user_name,
            schedule_date=schedule.schedule_date,
            unit_id=schedule.unit_id,
            shift_id=schedule.shift_id,
        )
    if event_type == "check_out" and "check_in" not in existing_types:
        await db.rollback()
        return CheckInResponse(
            success=False,
            status="not_checked_in",
            message=f"You have not checked in for this shift, {user_name}.",
            user_id=user_id,
            user_name=user_name,
            schedule_date=schedule.schedule_date,
            unit_id=schedule.unit_id,
            shift_id=schedule.shift_id,
        )
    if event_type == "check_out" and "check_out" in existing_types:
        await db.rollback()
        return CheckInResponse(
            success=False,
            status="already_checked_out",
            message=f"You have already checked out for this shift, {user_name}.",
            user_id=user_id,
            user_name=user_name,
            schedule_date=schedule.schedule_date,
            unit_id=schedule.unit_id,
            shift_id=schedule.shift_id,
        )

    result_status = attendance_status(event_type, event_time, schedule)
    log = AttendanceLog(
        org_id=org.id,
        user_id=user_id,
        device_id=device.id,
        unit_id=schedule.unit_id,
        shift_id=schedule.shift_id,
        schedule_date=schedule.schedule_date,
        ts=event_time,
        type=event_type,
        status=result_status,
        confidence_score=identity_match.score,
        source="face",
    )
    db.add(log)
    await db.commit()
    return CheckInResponse(
        success=True,
        status=result_status,
        message=(
            f"Welcome, {user_name}."
            if event_type == "check_in"
            else f"Goodbye, {user_name}."
        ),
        user_id=user_id,
        user_name=user_name,
        event_time=log.ts,
        schedule_date=log.schedule_date,
        unit_id=log.unit_id,
        shift_id=log.shift_id,
        confidence_score=identity_match.score,
    )


@router.post("/check-in", response_model=CheckInResponse)
async def check_in(
    request: CheckInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    device: Annotated[Device, Depends(require_device)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> CheckInResponse:
    return await process_attendance("check_in", request, db, device, face_client)


@router.post("/check-out", response_model=CheckInResponse)
async def check_out(
    request: CheckInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    device: Annotated[Device, Depends(require_device)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> CheckInResponse:
    return await process_attendance("check_out", request, db, device, face_client)

async def log_response(db: AsyncSession, log: AttendanceLog) -> AttendanceLogResponse:
    names = (
        await db.execute(
            select(
                User.name,
                Device.name,
                OrganizationalUnit.name,
                Shift.name,
            )
            .outerjoin(Device, Device.id == log.device_id)
            .outerjoin(OrganizationalUnit, OrganizationalUnit.id == log.unit_id)
            .outerjoin(Shift, Shift.id == log.shift_id)
            .where(User.id == log.user_id)
        )
    ).first()
    return AttendanceLogResponse(
        id=log.id,
        user_id=log.user_id,
        user_name=names[0] if names else None,
        device_id=log.device_id,
        device_name=names[1] if names else None,
        unit_id=log.unit_id,
        unit_name=names[2] if names else None,
        shift_id=log.shift_id,
        shift_name=names[3] if names else None,
        schedule_date=log.schedule_date,
        event_time=log.ts,
        type=log.type,
        status=log.status,
        source=log.source,
        confidence_score=log.confidence_score,
        supersedes_id=log.supersedes_id,
        correction_reason=log.correction_reason,
        created_by_id=log.created_by_id,
    )


@router.post("/{log_id}/corrections", response_model=AttendanceLogResponse)
async def correct_attendance(
    log_id: UUID,
    payload: AttendanceCorrectionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> AttendanceLogResponse:
    original = await db.scalar(
        select(AttendanceLog).where(
            AttendanceLog.id == log_id,
            AttendanceLog.org_id == current_user.org_id,
        )
    )
    if original is None:
        raise HTTPException(status_code=404, detail="Attendance log not found")
    target_user_id = payload.user_id or original.user_id
    if target_user_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CORRECTION_USER_REQUIRED",
                "message": "A user is required when correcting an unidentified attempt",
            },
        )
    target_user = await load_user(db, current_user.org_id, target_user_id)
    if not target_user.is_active:
        raise HTTPException(status_code=409, detail="Cannot assign attendance to an inactive user")
    scope_ids: set[UUID] | None = None
    if current_user.role == UserRole.MANAGER.value:
        scope_ids = await managed_unit_ids(db, current_user)
        if original.unit_id is not None and original.unit_id not in scope_ids:
            raise HTTPException(status_code=403, detail="Attendance log is outside managed scope")
    org = await load_org(db, current_user.org_id)
    correction = await correct_attendance_log(
        db,
        original_id=log_id,
        org_id=org.id,
        actor=current_user,
        user=target_user,
        event_time=payload.event_time,
        event_type=payload.type,
        explicit_status=payload.status,
        reason=payload.reason,
        timezone_name=org.timezone,
    )
    if (
        current_user.role == UserRole.MANAGER.value
        and (
            scope_ids is None
            or correction.unit_id is None
            or correction.unit_id not in scope_ids
        )
    ):
        await db.rollback()
        raise HTTPException(status_code=403, detail="Corrected event is outside managed scope")
    await db.commit()
    return await log_response(db, correction)


async def query_attendance_logs(
    db: AsyncSession,
    org: Org,
    user_id: UUID | None,
    device_id: UUID | None,
    unit_id: UUID | None,
    shift_id: UUID | None,
    from_date: date | None,
    to_date: date | None,
    attendance_status: str | None,
    attendance_type: str | None,
    page: int,
    page_size: int,
    scope_unit_ids: set[UUID] | None = None,
) -> PaginatedResponse[AttendanceLogResponse]:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must not exceed to_date")
    conditions: list[ColumnElement[bool]] = [
        AttendanceLog.org_id == org.id,
        effective_attendance_condition(),
    ]
    if scope_unit_ids is not None:
        conditions.append(AttendanceLog.unit_id.in_(scope_unit_ids))
    if user_id is not None:
        conditions.append(AttendanceLog.user_id == user_id)
    if device_id is not None:
        conditions.append(AttendanceLog.device_id == device_id)
    if unit_id is not None:
        conditions.append(AttendanceLog.unit_id == unit_id)
    if shift_id is not None:
        conditions.append(AttendanceLog.shift_id == shift_id)
    if from_date is not None:
        conditions.append(AttendanceLog.schedule_date >= from_date)
    if to_date is not None:
        conditions.append(AttendanceLog.schedule_date <= to_date)
    if attendance_status is not None:
        conditions.append(AttendanceLog.status == attendance_status)
    if attendance_type is not None:
        conditions.append(AttendanceLog.type == attendance_type)

    total = await db.scalar(select(func.count(AttendanceLog.id)).where(*conditions)) or 0
    rows = (
        await db.execute(
            select(
                AttendanceLog,
                User.name.label("user_name"),
                Device.name.label("device_name"),
                OrganizationalUnit.name.label("unit_name"),
                Shift.name.label("shift_name"),
            )
            .outerjoin(User, AttendanceLog.user_id == User.id)
            .outerjoin(Device, AttendanceLog.device_id == Device.id)
            .outerjoin(OrganizationalUnit, AttendanceLog.unit_id == OrganizationalUnit.id)
            .outerjoin(Shift, AttendanceLog.shift_id == Shift.id)
            .where(*conditions)
            .order_by(AttendanceLog.ts.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [
        AttendanceLogResponse(
            id=row[0].id,
            user_id=row[0].user_id,
            user_name=row[1],
            device_id=row[0].device_id,
            device_name=row[2],
            unit_id=row[0].unit_id,
            unit_name=row[3],
            shift_id=row[0].shift_id,
            shift_name=row[4],
            schedule_date=row[0].schedule_date,
            event_time=row[0].ts,
            type=row[0].type,
            status=row[0].status,
            source=row[0].source,
            confidence_score=row[0].confidence_score,
            supersedes_id=row[0].supersedes_id,
            correction_reason=row[0].correction_reason,
            created_by_id=row[0].created_by_id,
        )
        for row in rows
    ]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 1,
    )


@router.get("", response_model=PaginatedResponse[AttendanceLogResponse])
async def list_attendance(
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    user_id: Annotated[UUID | None, Query(description="Filter by user ID")] = None,
    device_id: Annotated[UUID | None, Query(description="Filter by device ID")] = None,
    unit_id: Annotated[UUID | None, Query(description="Filter by unit ID")] = None,
    shift_id: Annotated[UUID | None, Query(description="Filter by shift ID")] = None,
    from_date: Annotated[date | None, Query(description="Start date filter")] = None,
    to_date: Annotated[date | None, Query(description="End date filter")] = None,
    attendance_status: Annotated[str | None, Query(alias="status")] = None,
    attendance_type: Annotated[str | None, Query(alias="type")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[AttendanceLogResponse]:
    if identity.kind == "device":
        raise HTTPException(status_code=403, detail="User authentication required")
    effective_user_id = user_id
    if identity.role is None or identity.role.value not in OPERATOR_ROLES:
        effective_user_id = identity.subject_id
    org = await load_org(db, identity.org_id)
    scope_unit_ids: set[UUID] | None = None
    if identity.role is not None and identity.role.value == "manager":
        actor = await db.get(User, identity.subject_id)
        if actor is None:
            raise HTTPException(status_code=401, detail="User account is inactive or missing")
        scope_unit_ids = await managed_unit_ids(db, actor)
        if unit_id is not None and unit_id not in scope_unit_ids:
            raise HTTPException(status_code=403, detail="Unit is outside managed scope")
        if effective_user_id is not None:
            target = await load_user(db, identity.org_id, effective_user_id)
            await ensure_user_in_scope(db, actor, target)
    return await query_attendance_logs(
        db=db,
        org=org,
        user_id=effective_user_id,
        device_id=device_id,
        unit_id=unit_id,
        shift_id=shift_id,
        from_date=from_date,
        to_date=to_date,
        attendance_status=attendance_status,
        attendance_type=attendance_type,
        page=page,
        page_size=page_size,
        scope_unit_ids=scope_unit_ids,
    )


@router.get("/daily", response_model=DailyAttendanceResponse)
async def get_daily_attendance(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    target_date: Annotated[date | None, Query(alias="date")] = None,
    unit_id: Annotated[UUID | None, Query()] = None,
    shift_id: Annotated[UUID | None, Query()] = None,
) -> DailyAttendanceResponse:
    org = await load_org(db, current_user.org_id)
    day = target_date or local_day_bounds(org.timezone)[0]
    scope_ids: set[UUID] | None = None
    if current_user.role == UserRole.MANAGER.value:
        scope_ids = await managed_unit_ids(db, current_user)
        if unit_id is not None and unit_id not in scope_ids:
            raise HTTPException(status_code=403, detail="Unit is outside managed scope")
    schedule_rows = await schedule_rows_for_date(
        db,
        org_id=org.id,
        timezone_name=org.timezone,
        schedule_date=day,
        scope_unit_ids=scope_ids,
        unit_id=unit_id,
        shift_id=shift_id,
    )
    conditions: list[ColumnElement[bool]] = [
        AttendanceLog.org_id == org.id,
        AttendanceLog.schedule_date == day,
        effective_attendance_condition(),
    ]
    if scope_ids is not None:
        conditions.append(AttendanceLog.unit_id.in_(scope_ids))
    if unit_id is not None:
        conditions.append(AttendanceLog.unit_id == unit_id)
    if shift_id is not None:
        conditions.append(AttendanceLog.shift_id == shift_id)
    logs = list(
        (
            await db.scalars(
                select(AttendanceLog)
                .where(*conditions)
                .order_by(AttendanceLog.ts, AttendanceLog.id)
            )
        ).all()
    )
    identified_logs = [log for log in logs if log.user_id is not None]
    schedule_by_user = {user.id: (user, schedule) for user, schedule in schedule_rows}
    missing_user_ids = {
        log.user_id
        for log in identified_logs
        if log.user_id is not None and log.user_id not in schedule_by_user
    }
    if missing_user_ids:
        missing_users = list(
            (
                await db.scalars(
                    select(User)
                    .where(User.id.in_(missing_user_ids))
                    .order_by(User.name, User.id)
                )
            ).all()
        )
        for user in missing_users:
            schedule = await resolve_schedule_for_event(
                db,
                org_id=org.id,
                timezone_name=org.timezone,
                user_id=user.id,
                event_time=next(
                    log.ts for log in identified_logs if log.user_id == user.id
                ),
            )
            schedule_by_user[user.id] = (user, schedule)
    logs_by_user: dict[UUID, dict[str, AttendanceLog]] = {}
    for log in identified_logs:
        if log.user_id is not None:
            logs_by_user.setdefault(log.user_id, {})[log.type] = log
    rows: list[DailyAttendanceUser] = []
    for user, schedule in schedule_by_user.values():
        user_logs = logs_by_user.get(user.id, {})
        check_in = user_logs.get("check_in")
        check_out = user_logs.get("check_out")
        rows.append(
            DailyAttendanceUser(
                user_id=user.id,
                user_name=user.name,
                unit_id=schedule.unit_id,
                unit_name=None,
                shift_id=schedule.shift_id,
                shift_name=schedule.shift.name if schedule.shift else None,
                scheduled=schedule.scheduled,
                check_in=await log_response(db, check_in) if check_in else None,
                check_out=await log_response(db, check_out) if check_out else None,
                status=(
                    check_in.status
                    if check_in is not None
                    else "absent"
                    if schedule.scheduled
                    else "not_scheduled"
                ),
            )
        )
    unit_rows = (
        await db.execute(
            select(OrganizationalUnit.id, OrganizationalUnit.name).where(
                OrganizationalUnit.id.in_({row.unit_id for row in rows if row.unit_id is not None})
            )
        )
    ).all()
    unit_names: dict[UUID, str] = {unit_id: name for unit_id, name in unit_rows}
    rows = [
        row.model_copy(
            update={"unit_name": unit_names.get(row.unit_id) if row.unit_id is not None else None}
        )
        for row in rows
    ]
    scheduled_count = sum(row.scheduled for row in rows)
    present_count = sum(row.check_in is not None for row in rows)
    return DailyAttendanceResponse(
        date=day,
        scheduled=scheduled_count,
        present=present_count,
        absent=max(0, scheduled_count - present_count),
        users=rows,
        unknown_attempts=sum(log.status == "unknown_user" for log in logs),
        ambiguous_attempts=sum(log.status == "ambiguous_face" for log in logs),
    )


@router.get("/summary/daily", response_model=DailySummary)
async def get_daily_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    target_date: Annotated[date | None, Query()] = None,
) -> DailySummary:
    daily = await get_daily_attendance(
        db=db,
        current_user=current_user,
        target_date=target_date,
        unit_id=None,
        shift_id=None,
    )
    on_time = sum(row.status == "on_time" for row in daily.users)
    late = sum(row.status == "late" for row in daily.users)
    return DailySummary(
        date=daily.date,
        scheduled=daily.scheduled,
        checked_in=daily.present,
        on_time=on_time,
        late=late,
        absent=daily.absent,
        unknown_attempts=daily.unknown_attempts,
        ambiguous_attempts=daily.ambiguous_attempts,
    )


@router.get("/me", response_model=PaginatedResponse[AttendanceLogResponse])
async def get_my_attendance(
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    from_date: Annotated[date | None, Query(description="Start date filter")] = None,
    to_date: Annotated[date | None, Query(description="End date filter")] = None,
    attendance_status: Annotated[str | None, Query(alias="status")] = None,
    attendance_type: Annotated[str | None, Query(alias="type")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[AttendanceLogResponse]:
    if identity.kind != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User authentication required",
        )
    org = await load_org(db, identity.org_id)
    return await query_attendance_logs(
        db=db,
        org=org,
        user_id=identity.subject_id,
        device_id=None,
        unit_id=None,
        shift_id=None,
        from_date=from_date,
        to_date=to_date,
        attendance_status=attendance_status,
        attendance_type=attendance_type,
        page=page,
        page_size=page_size,
    )
