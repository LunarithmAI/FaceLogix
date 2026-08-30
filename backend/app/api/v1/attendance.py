from datetime import date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OPERATOR_ROLES, get_current_identity
from app.api.tenant import load_device, load_org, load_user
from app.core.database import get_db
from app.core.identity import AuthenticatedIdentity
from app.core.images import ImagePayloadError, decode_image_payload
from app.core.time import local_date_bounds, local_day_bounds, local_time, utc_now
from app.models.attendance_log import AttendanceLog
from app.models.device import Device
from app.models.org import Org
from app.models.user import User
from app.schemas.attendance import (
    AttendanceLogResponse,
    CheckInRequest,
    CheckInResponse,
    DailySummary,
)
from app.schemas.common import PaginatedResponse
from app.schemas.settings import OrgSettingsData, canonical_org_settings
from app.services.face_client import (
    FaceAnalysis,
    FaceServiceClient,
    FaceServiceError,
    get_face_client,
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


async def find_similar_faces(
    db: AsyncSession,
    embedding: list[float],
    org_id: UUID,
    limit: int = 1,
    threshold: float = 0.75,
) -> list[tuple[UUID, float]]:
    embedding_str = f"[{','.join(map(str, embedding))}]"
    query = text(
        """
        SELECT
            fe.user_id,
            1 - (fe.embedding <=> CAST(:embedding AS vector)) AS score
        FROM face_embeddings fe
        JOIN users u ON fe.user_id = u.id
        WHERE u.org_id = CAST(:org_id AS uuid)
          AND u.is_active = TRUE
          AND 1 - (fe.embedding <=> CAST(:embedding AS vector)) >= :threshold
        ORDER BY fe.embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
        """
    )
    result = await db.execute(
        query,
        {
            "embedding": embedding_str,
            "org_id": str(org_id),
            "threshold": threshold,
            "limit": limit,
        },
    )
    return [(UUID(str(row[0])), float(row[1])) for row in result.fetchall()]


def calculate_check_in_status(
    org: Org,
    policy: OrgSettingsData,
    check_time: datetime,
) -> str:
    local_check_time = local_time(org.timezone, check_time)
    start_hour, start_minute = map(int, policy.work_start_time.split(":"))
    deadline = local_check_time.replace(
        hour=start_hour,
        minute=start_minute,
        second=0,
        microsecond=0,
    ) + timedelta(minutes=policy.late_threshold_minutes)
    return "on_time" if local_check_time <= deadline else "late"


def face_failure_response(error: ImagePayloadError | FaceServiceError) -> CheckInResponse:
    mapped = ATTENDANCE_FACE_STATUSES.get(error.code)
    if mapped is not None:
        return CheckInResponse(success=False, status=mapped[0], message=mapped[1])
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


async def effective_device_id(
    db: AsyncSession,
    identity: AuthenticatedIdentity,
    requested_device_id: UUID | None,
) -> UUID | None:
    if identity.kind == "device":
        return identity.subject_id
    if requested_device_id is None:
        return None
    device = await load_device(db, identity.org_id, requested_device_id)
    if not device.is_active:
        raise HTTPException(status_code=404, detail="Device not found")
    return device.id


async def analyze_attendance_image(
    request: CheckInRequest,
    face_client: FaceServiceClient,
) -> FaceAnalysis | CheckInResponse:
    try:
        image_bytes = decode_image_payload(request.image)
        return await face_client.analyze(image_bytes)
    except (ImagePayloadError, FaceServiceError) as exc:
        return face_failure_response(exc)


async def process_attendance(
    event_type: str,
    request: CheckInRequest,
    db: AsyncSession,
    identity: AuthenticatedIdentity,
    face_client: FaceServiceClient,
) -> CheckInResponse:
    org = await load_org(db, identity.org_id)
    policy = canonical_org_settings(org.settings)
    device_id = await effective_device_id(db, identity, request.device_id)
    analysis = await analyze_attendance_image(request, face_client)
    if isinstance(analysis, CheckInResponse):
        return analysis
    if policy.require_liveness and analysis.pad_live_score < policy.liveness_threshold:
        return CheckInResponse(
            success=False,
            status="spoof_detected",
            message="Liveness verification failed. Please try again in person.",
        )

    matches = await find_similar_faces(
        db,
        analysis.embedding,
        identity.org_id,
        threshold=policy.face_match_threshold,
    )
    now = utc_now()
    if not matches:
        if event_type == "check_in":
            db.add(
                AttendanceLog(
                    org_id=identity.org_id,
                    device_id=device_id,
                    ts=now,
                    type=event_type,
                    status="unknown_user",
                    confidence_score=analysis.quality_score,
                )
            )
            await db.commit()
        return CheckInResponse(
            success=False,
            status="unknown_user",
            message="Face not recognized. Please contact an administrator.",
        )

    user_id, score = matches[0]
    user = await load_user(db, identity.org_id, user_id)
    if not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    _, day_start, day_end = local_day_bounds(org.timezone, now)
    existing_types = set(
        (
            await db.scalars(
                select(AttendanceLog.type).where(
                    AttendanceLog.user_id == user_id,
                    AttendanceLog.ts >= day_start,
                    AttendanceLog.ts < day_end,
                    AttendanceLog.status != "unknown_user",
                )
            )
        ).all()
    )
    if event_type == "check_in" and "check_in" in existing_types:
        return CheckInResponse(
            success=False,
            status="already_checked_in",
            message=f"You have already checked in today, {user.name}.",
            user_id=user.id,
            user_name=user.name,
        )
    if event_type == "check_out":
        if "check_in" not in existing_types:
            return CheckInResponse(
                success=False,
                status="not_checked_in",
                message=f"You have not checked in today, {user.name}.",
                user_id=user.id,
                user_name=user.name,
            )
        if "check_out" in existing_types:
            return CheckInResponse(
                success=False,
                status="already_checked_out",
                message=f"You have already checked out today, {user.name}.",
                user_id=user.id,
                user_name=user.name,
            )

    attendance_status = (
        calculate_check_in_status(org, policy, now) if event_type == "check_in" else "on_time"
    )
    log = AttendanceLog(
        org_id=identity.org_id,
        user_id=user.id,
        device_id=device_id,
        ts=now,
        type=event_type,
        status=attendance_status,
        confidence_score=score,
    )
    db.add(log)
    await db.commit()
    if event_type == "check_in":
        message = (
            f"Welcome, {user.name}!"
            if attendance_status == "on_time"
            else f"Welcome, {user.name}. You are late."
        )
    else:
        message = f"Goodbye, {user.name}! Have a great day."
    return CheckInResponse(
        success=True,
        status=attendance_status,
        message=message,
        user_id=user.id,
        user_name=user.name,
        check_in_time=log.ts,
        confidence_score=score,
    )


@router.post("/check-in", response_model=CheckInResponse)
async def check_in(
    request: CheckInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> CheckInResponse:
    return await process_attendance("check_in", request, db, identity, face_client)


@router.post("/check-out", response_model=CheckInResponse)
async def check_out(
    request: CheckInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> CheckInResponse:
    return await process_attendance("check_out", request, db, identity, face_client)


async def query_attendance_logs(
    db: AsyncSession,
    org: Org,
    user_id: UUID | None,
    device_id: UUID | None,
    from_date: date | None,
    to_date: date | None,
    attendance_status: str | None,
    attendance_type: str | None,
    page: int,
    page_size: int,
) -> PaginatedResponse[AttendanceLogResponse]:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must not exceed to_date")
    conditions = [AttendanceLog.org_id == org.id]
    if user_id is not None:
        conditions.append(AttendanceLog.user_id == user_id)
    if device_id is not None:
        conditions.append(AttendanceLog.device_id == device_id)
    if from_date is not None:
        range_start, _ = local_date_bounds(org.timezone, from_date)
        conditions.append(AttendanceLog.ts >= range_start)
    if to_date is not None:
        _, range_end = local_date_bounds(org.timezone, to_date)
        conditions.append(AttendanceLog.ts < range_end)
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
            )
            .outerjoin(User, AttendanceLog.user_id == User.id)
            .outerjoin(Device, AttendanceLog.device_id == Device.id)
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
            ts=row[0].ts,
            type=row[0].type,
            status=row[0].status,
            confidence_score=row[0].confidence_score,
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
    return await query_attendance_logs(
        db,
        org,
        effective_user_id,
        device_id,
        from_date,
        to_date,
        attendance_status,
        attendance_type,
        page,
        page_size,
    )


@router.get("/summary/daily", response_model=DailySummary)
async def get_daily_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    target_date: Annotated[date | None, Query()] = None,
) -> DailySummary:
    if (
        identity.kind != "user"
        or identity.role is None
        or identity.role.value not in OPERATOR_ROLES
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operational access required",
        )
    org = await load_org(db, identity.org_id)
    current_date, current_start, current_end = local_day_bounds(org.timezone)
    summary_date = target_date or current_date
    start, end = (
        (current_start, current_end)
        if target_date is None
        else local_date_bounds(org.timezone, target_date)
    )
    total_users = (
        await db.scalar(
            select(func.count(User.id)).where(
                User.org_id == org.id,
                User.is_active.is_(True),
            )
        )
        or 0
    )
    rows = (
        await db.execute(
            select(
                AttendanceLog.status,
                func.count(func.distinct(AttendanceLog.user_id)),
            )
            .where(
                AttendanceLog.org_id == org.id,
                AttendanceLog.type == "check_in",
                AttendanceLog.ts >= start,
                AttendanceLog.ts < end,
            )
            .group_by(AttendanceLog.status)
        )
    ).all()
    counts = {row[0]: int(row[1]) for row in rows}
    on_time = counts.get("on_time", 0)
    late = counts.get("late", 0)
    checked_in = on_time + late
    return DailySummary(
        date=summary_date,
        total_users=total_users,
        checked_in=checked_in,
        on_time=on_time,
        late=late,
        absent=max(0, total_users - checked_in),
        unknown_attempts=counts.get("unknown_user", 0),
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
        db,
        org,
        identity.subject_id,
        None,
        from_date,
        to_date,
        attendance_status,
        attendance_type,
        page,
        page_size,
    )
