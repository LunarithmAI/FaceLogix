"""
Attendance endpoints for FaceLogix.

Provides check-in/check-out functionality with face recognition and attendance logs.
"""

from datetime import date, datetime, time, timedelta
from typing import List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_identity, get_db, require_admin
from app.core.config import settings
from app.models.attendance_log import AttendanceLog
from app.models.device import Device
from app.models.org import Org
from app.models.user import User
from app.schemas.attendance import (
    AttendanceLogResponse,
    CheckInResponse,
    DailySummary,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/attendance", tags=["Attendance"])


async def find_similar_faces(
    db: AsyncSession,
    embedding: List[float],
    org_id: str,
    limit: int = 1,
    threshold: float = 0.75,
) -> List[tuple]:
    """
    Find similar faces using cosine similarity with pgvector.
    Returns list of (user_id, similarity_score) tuples.
    """
    embedding_str = f"[{','.join(map(str, embedding))}]"
    
    query = text("""
        SELECT 
            fe.user_id::text,
            1 - (fe.embedding <=> :embedding::vector) AS score
        FROM face_embeddings fe
        JOIN users u ON fe.user_id = u.id
        WHERE u.org_id = :org_id::uuid 
          AND u.is_active = TRUE
          AND 1 - (fe.embedding <=> :embedding::vector) >= :threshold
        ORDER BY fe.embedding <=> :embedding::vector
        LIMIT :limit
    """)
    
    result = await db.execute(query, {
        "embedding": embedding_str,
        "org_id": org_id,
        "threshold": threshold,
        "limit": limit,
    })
    
    return [(str(row[0]), row[1]) for row in result.fetchall()]


def calculate_check_in_status(org: Org, check_time: datetime) -> str:
    """Calculate check-in status based on org settings."""
    org_settings = org.settings or {}
    
    # Get settings with defaults
    check_in_end = org_settings.get("check_in_end", "09:30")
    late_threshold_minutes = org_settings.get("late_threshold_minutes", 15)
    
    # Parse check_in_end time
    try:
        end_hour, end_minute = map(int, check_in_end.split(":"))
    except (ValueError, AttributeError):
        end_hour, end_minute = 9, 30
    
    # Create deadline in the same timezone as check_time
    deadline = check_time.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    
    if check_time <= deadline:
        return "on_time"
    elif check_time <= deadline + timedelta(minutes=late_threshold_minutes):
        return "late"
    else:
        return "late"


@router.post("/check-in", response_model=CheckInResponse)
async def check_in(
    image: UploadFile = File(..., description="Face image for recognition"),
    device_id: Optional[UUID] = Form(None, description="Device ID if checking in from device"),
    db: AsyncSession = Depends(get_db),
    identity: dict = Depends(get_current_identity),
):
    """
    Process check-in request with face recognition.
    
    The image is processed through the face service to generate an embedding,
    which is then matched against enrolled users in the organization.
    
    Can be called with either user token or device token.
    """
    # Read image content
    content = await image.read()
    
    # Get embedding from face service
    try:
        async with httpx.AsyncClient(timeout=settings.FACE_SERVICE_TIMEOUT) as client:
            response = await client.post(
                f"{settings.FACE_SERVICE_URL}/api/v1/embed",
                files={"image": (image.filename or "face.jpg", content, image.content_type or "image/jpeg")},
            )
            
            if response.status_code == 400:
                # No face detected
                return CheckInResponse(
                    success=False,
                    status="no_face_detected",
                    message="No face detected in the image. Please try again.",
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Face recognition service unavailable",
                )
            
            embedding_result = response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Face recognition service timeout",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face recognition service unavailable",
        )
    
    org_id = identity["org_id"]
    embedding = embedding_result.get("embedding")
    quality_score = embedding_result.get("quality_score", 1.0)
    
    # Determine effective device_id
    effective_device_id = device_id
    if identity["type"] == "device":
        effective_device_id = UUID(identity["sub"])
    
    # Get recognition threshold from org settings
    org = await db.get(Org, UUID(org_id))
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    threshold = org.settings.get("recognition_threshold", settings.DEFAULT_RECOGNITION_THRESHOLD)
    
    # Find matching user
    matches = await find_similar_faces(
        db=db,
        embedding=embedding,
        org_id=org_id,
        limit=1,
        threshold=threshold,
    )
    
    if not matches:
        # Unknown user - log the attempt
        log = AttendanceLog(
            org_id=UUID(org_id),
            device_id=effective_device_id,
            ts=datetime.utcnow(),
            type="check_in",
            status="unknown_user",
            confidence_score=quality_score,
        )
        db.add(log)
        await db.commit()
        
        return CheckInResponse(
            success=False,
            status="unknown_user",
            message="Face not recognized. Please contact administrator.",
        )
    
    user_id, score = matches[0]
    user_id = UUID(user_id)
    
    # Check if already checked in today
    today_start = datetime.combine(date.today(), time.min)
    existing = await db.execute(
        select(AttendanceLog).where(
            and_(
                AttendanceLog.user_id == user_id,
                AttendanceLog.type == "check_in",
                AttendanceLog.ts >= today_start,
                AttendanceLog.status != "unknown_user",
            )
        )
    )
    
    if existing.scalar_one_or_none():
        user = await db.get(User, user_id)
        return CheckInResponse(
            success=False,
            status="already_checked_in",
            message=f"You have already checked in today, {user.name}.",
            user_id=user_id,
            user_name=user.name if user else None,
        )
    
    # Get user details
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Calculate status
    check_status = calculate_check_in_status(org, datetime.utcnow())
    
    # Create attendance log
    log = AttendanceLog(
        org_id=UUID(org_id),
        user_id=user_id,
        device_id=effective_device_id,
        ts=datetime.utcnow(),
        type="check_in",
        status=check_status,
        confidence_score=score,
    )
    db.add(log)
    await db.commit()
    
    # Create response message
    if check_status == "on_time":
        message = f"Welcome, {user.name}!"
    else:
        message = f"Welcome, {user.name}. You are late."
    
    return CheckInResponse(
        success=True,
        status=check_status,
        message=message,
        user_id=user_id,
        user_name=user.name,
        check_in_time=log.ts,
        confidence_score=score,
    )


@router.post("/check-out", response_model=CheckInResponse)
async def check_out(
    image: UploadFile = File(..., description="Face image for recognition"),
    device_id: Optional[UUID] = Form(None, description="Device ID if checking out from device"),
    db: AsyncSession = Depends(get_db),
    identity: dict = Depends(get_current_identity),
):
    """
    Process check-out request with face recognition.
    
    Similar to check-in but records a check-out event.
    """
    # Read image content
    content = await image.read()
    
    # Get embedding from face service
    try:
        async with httpx.AsyncClient(timeout=settings.FACE_SERVICE_TIMEOUT) as client:
            response = await client.post(
                f"{settings.FACE_SERVICE_URL}/api/v1/embed",
                files={"image": (image.filename or "face.jpg", content, image.content_type or "image/jpeg")},
            )
            
            if response.status_code == 400:
                return CheckInResponse(
                    success=False,
                    status="no_face_detected",
                    message="No face detected in the image. Please try again.",
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Face recognition service unavailable",
                )
            
            embedding_result = response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Face recognition service timeout",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face recognition service unavailable",
        )
    
    org_id = identity["org_id"]
    embedding = embedding_result.get("embedding")
    
    # Determine effective device_id
    effective_device_id = device_id
    if identity["type"] == "device":
        effective_device_id = UUID(identity["sub"])
    
    # Get org and threshold
    org = await db.get(Org, UUID(org_id))
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    threshold = org.settings.get("recognition_threshold", settings.DEFAULT_RECOGNITION_THRESHOLD)
    
    # Find matching user
    matches = await find_similar_faces(
        db=db,
        embedding=embedding,
        org_id=org_id,
        limit=1,
        threshold=threshold,
    )
    
    if not matches:
        return CheckInResponse(
            success=False,
            status="unknown_user",
            message="Face not recognized. Please contact administrator.",
        )
    
    user_id, score = matches[0]
    user_id = UUID(user_id)
    
    # Get user details
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Create check-out log
    log = AttendanceLog(
        org_id=UUID(org_id),
        user_id=user_id,
        device_id=effective_device_id,
        ts=datetime.utcnow(),
        type="check_out",
        status="on_time",
        confidence_score=score,
    )
    db.add(log)
    await db.commit()
    
    return CheckInResponse(
        success=True,
        status="on_time",
        message=f"Goodbye, {user.name}! Have a great day.",
        user_id=user_id,
        user_name=user.name,
        check_in_time=log.ts,
        confidence_score=score,
    )


@router.get("", response_model=PaginatedResponse[AttendanceLogResponse])
async def list_attendance(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    device_id: Optional[UUID] = Query(None, description="Filter by device ID"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    attendance_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    attendance_type: Optional[str] = Query(None, alias="type", description="Filter by type (check_in/check_out)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    identity: dict = Depends(get_current_identity),
):
    """
    List attendance logs with filters and pagination.
    
    Admins see all logs in the organization.
    Members can only see their own attendance records.
    """
    org_id = UUID(identity["org_id"])
    
    # Base query with joins for user and device names
    query = (
        select(
            AttendanceLog,
            User.name.label("user_name"),
            Device.name.label("device_name"),
        )
        .outerjoin(User, AttendanceLog.user_id == User.id)
        .outerjoin(Device, AttendanceLog.device_id == Device.id)
        .where(AttendanceLog.org_id == org_id)
    )
    
    count_query = select(func.count(AttendanceLog.id)).where(AttendanceLog.org_id == org_id)
    
    # Non-admins can only see their own attendance
    effective_user_id = user_id
    if identity["type"] == "user" and identity.get("role") not in ("admin", "super_admin"):
        effective_user_id = UUID(identity["sub"])
    
    # Apply filters
    if effective_user_id:
        query = query.where(AttendanceLog.user_id == effective_user_id)
        count_query = count_query.where(AttendanceLog.user_id == effective_user_id)
    
    if device_id:
        query = query.where(AttendanceLog.device_id == device_id)
        count_query = count_query.where(AttendanceLog.device_id == device_id)
    
    if from_date:
        from_datetime = datetime.combine(from_date, time.min)
        query = query.where(AttendanceLog.ts >= from_datetime)
        count_query = count_query.where(AttendanceLog.ts >= from_datetime)
    
    if to_date:
        to_datetime = datetime.combine(to_date, time.max)
        query = query.where(AttendanceLog.ts <= to_datetime)
        count_query = count_query.where(AttendanceLog.ts <= to_datetime)
    
    if attendance_status:
        query = query.where(AttendanceLog.status == attendance_status)
        count_query = count_query.where(AttendanceLog.status == attendance_status)
    
    if attendance_type:
        query = query.where(AttendanceLog.type == attendance_type)
        count_query = count_query.where(AttendanceLog.type == attendance_type)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Calculate pagination
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Execute query with pagination
    query = query.order_by(AttendanceLog.ts.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for row in rows:
        log = row[0]
        items.append(
            AttendanceLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_name=row[1],  # user_name from join
                device_id=log.device_id,
                device_name=row[2],  # device_name from join
                ts=log.ts,
                type=log.type,
                status=log.status,
                confidence_score=log.confidence_score,
            )
        )
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/summary/daily", response_model=DailySummary)
async def get_daily_summary(
    target_date: Optional[date] = Query(None, description="Date for summary (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    identity: dict = Depends(get_current_identity),
):
    """
    Get daily attendance summary.
    
    Admin only.
    """
    # Check admin access
    if identity.get("role") not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    org_id = UUID(identity["org_id"])
    summary_date = target_date or date.today()
    
    # Get total active users
    total_users_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.org_id == org_id,
                User.is_active == True,
            )
        )
    )
    total_users = total_users_result.scalar() or 0
    
    # Get attendance counts by status
    start = datetime.combine(summary_date, time.min)
    end = datetime.combine(summary_date, time.max)
    
    status_counts_result = await db.execute(
        select(
            AttendanceLog.status,
            func.count(func.distinct(AttendanceLog.user_id)),
        )
        .where(
            and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.type == "check_in",
                AttendanceLog.ts >= start,
                AttendanceLog.ts <= end,
            )
        )
        .group_by(AttendanceLog.status)
    )
    
    counts = {row[0]: row[1] for row in status_counts_result.fetchall()}
    
    on_time = counts.get("on_time", 0)
    late = counts.get("late", 0)
    unknown_attempts = counts.get("unknown_user", 0)
    checked_in = on_time + late
    absent = max(0, total_users - checked_in)
    
    return DailySummary(
        date=summary_date,
        total_users=total_users,
        checked_in=checked_in,
        on_time=on_time,
        late=late,
        absent=absent,
        unknown_attempts=unknown_attempts,
    )
