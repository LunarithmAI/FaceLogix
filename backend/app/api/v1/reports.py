"""
Reports endpoints for FaceLogix.

Provides attendance reports, CSV exports, and summary statistics.
"""

import io
from datetime import date, datetime, time, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.attendance_log import AttendanceLog
from app.models.device import Device
from app.models.user import User
from app.schemas.attendance import DailySummary

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get dashboard statistics including today's summary, 
    total users, active devices, and recent activity.
    
    Admin only.
    """
    org_id = current_user.org_id
    today = date.today()
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    
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
    
    # Get active devices
    active_devices_result = await db.execute(
        select(func.count(Device.id)).where(
            and_(
                Device.org_id == org_id,
                Device.is_active == True,
            )
        )
    )
    active_devices = active_devices_result.scalar() or 0
    
    # Get pending enrollments (users without face embeddings)
    pending_enrollments_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.org_id == org_id,
                User.is_active == True,
                User.enrolled_at == None,
            )
        )
    )
    pending_enrollments = pending_enrollments_result.scalar() or 0
    
    # Get today's check-in statistics
    check_in_stats = await db.execute(
        select(
            AttendanceLog.status,
            func.count(func.distinct(AttendanceLog.user_id)),
        )
        .where(
            and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.type == "check_in",
                AttendanceLog.ts >= start_of_day,
                AttendanceLog.ts <= end_of_day,
            )
        )
        .group_by(AttendanceLog.status)
    )
    check_in_counts = {row[0]: row[1] for row in check_in_stats.fetchall()}
    
    on_time = check_in_counts.get("on_time", 0)
    late = check_in_counts.get("late", 0)
    checked_in = on_time + late
    absent = max(0, total_users - checked_in)
    
    # Get today's check-out count
    check_out_result = await db.execute(
        select(func.count(func.distinct(AttendanceLog.user_id))).where(
            and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.type == "check_out",
                AttendanceLog.ts >= start_of_day,
                AttendanceLog.ts <= end_of_day,
            )
        )
    )
    checked_out = check_out_result.scalar() or 0
    
    # Get recent activity (last 10 records)
    recent_activity_result = await db.execute(
        select(
            AttendanceLog.id,
            AttendanceLog.ts,
            AttendanceLog.type,
            AttendanceLog.status,
            AttendanceLog.confidence_score,
            User.id.label("user_id"),
            User.name.label("user_name"),
        )
        .outerjoin(User, AttendanceLog.user_id == User.id)
        .where(AttendanceLog.org_id == org_id)
        .order_by(AttendanceLog.ts.desc())
        .limit(10)
    )
    
    recent_activity = []
    for row in recent_activity_result.fetchall():
        recent_activity.append({
            "id": str(row.id),
            "timestamp": row.ts.isoformat() if row.ts else None,
            "type": row.type,
            "status": row.status,
            "confidence_score": row.confidence_score,
            "user_id": str(row.user_id) if row.user_id else None,
            "user_name": row.user_name,
        })
    
    return {
        "today": {
            "date": today.isoformat(),
            "total_employees": total_users,
            "checked_in": checked_in,
            "checked_out": checked_out,
            "on_time": on_time,
            "late_arrivals": late,
            "absent": absent,
        },
        "total_users": total_users,
        "active_devices": active_devices,
        "pending_enrollments": pending_enrollments,
        "recent_activity": recent_activity,
    }


@router.get("/attendance/csv")
async def export_attendance_csv(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Export attendance logs as CSV.
    
    Admin only.
    """
    org_id = current_user.org_id
    
    # Build query
    query = (
        select(
            AttendanceLog.id,
            User.name,
            User.email,
            User.external_id,
            User.department,
            AttendanceLog.ts,
            AttendanceLog.type,
            AttendanceLog.status,
            AttendanceLog.confidence_score,
        )
        .outerjoin(User, AttendanceLog.user_id == User.id)
        .where(
            and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.ts >= datetime.combine(from_date, time.min),
                AttendanceLog.ts <= datetime.combine(to_date, time.max),
            )
        )
        .order_by(AttendanceLog.ts.desc())
    )
    
    if user_id:
        query = query.where(AttendanceLog.user_id == user_id)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    # Generate CSV
    output = io.StringIO()
    output.write("ID,Name,Email,External ID,Department,Timestamp,Type,Status,Confidence\n")
    
    for row in rows:
        line = ",".join([
            str(row[0]),  # id
            f'"{row[1] or ""}"',  # name
            f'"{row[2] or ""}"',  # email
            f'"{row[3] or ""}"',  # external_id
            f'"{row[4] or ""}"',  # department
            row[5].isoformat() if row[5] else "",  # ts
            row[6] or "",  # type
            row[7] or "",  # status
            f"{row[8]:.2f}" if row[8] else "",  # confidence
        ])
        output.write(line + "\n")
    
    output.seek(0)
    
    filename = f"attendance_{from_date}_{to_date}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/summary/weekly")
async def get_weekly_summary(
    week_start: date = Query(..., description="Start date of the week (Monday)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get weekly attendance summary with daily breakdown.
    
    Admin only.
    """
    org_id = current_user.org_id
    
    # Calculate week end (7 days)
    week_end = week_start + timedelta(days=6)
    
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
    
    # Get daily summaries
    daily_summaries = []
    
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        start = datetime.combine(current_date, time.min)
        end = datetime.combine(current_date, time.max)
        
        # Get status counts for the day
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
        
        daily_summaries.append(
            DailySummary(
                date=current_date,
                total_users=total_users,
                checked_in=checked_in,
                on_time=on_time,
                late=late,
                absent=absent,
                unknown_attempts=unknown_attempts,
            ).model_dump()
        )
    
    # Calculate weekly totals
    total_on_time = sum(d["on_time"] for d in daily_summaries)
    total_late = sum(d["late"] for d in daily_summaries)
    total_absent = sum(d["absent"] for d in daily_summaries)
    total_unknown = sum(d["unknown_attempts"] for d in daily_summaries)
    
    # Calculate averages
    avg_attendance_rate = (
        (total_on_time + total_late) / (total_users * 7) * 100
        if total_users > 0
        else 0
    )
    
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_users": total_users,
        "daily_summaries": daily_summaries,
        "weekly_totals": {
            "on_time": total_on_time,
            "late": total_late,
            "absent": total_absent,
            "unknown_attempts": total_unknown,
        },
        "average_attendance_rate": round(avg_attendance_rate, 2),
    }


@router.get("/summary/user/{user_id}")
async def get_user_summary(
    user_id: UUID,
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get attendance summary for a specific user.
    
    Admin only.
    """
    org_id = current_user.org_id
    
    # Verify user exists and belongs to org
    user = await db.get(User, user_id)
    if not user or user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get attendance counts by status
    status_counts_result = await db.execute(
        select(
            AttendanceLog.status,
            func.count(AttendanceLog.id),
        )
        .where(
            and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.user_id == user_id,
                AttendanceLog.type == "check_in",
                AttendanceLog.ts >= datetime.combine(from_date, time.min),
                AttendanceLog.ts <= datetime.combine(to_date, time.max),
            )
        )
        .group_by(AttendanceLog.status)
    )
    
    counts = {row[0]: row[1] for row in status_counts_result.fetchall()}
    
    on_time = counts.get("on_time", 0)
    late = counts.get("late", 0)
    total_check_ins = on_time + late
    
    # Calculate working days in range
    working_days = 0
    current = from_date
    while current <= to_date:
        if current.weekday() < 5:  # Monday to Friday
            working_days += 1
        current += timedelta(days=1)
    
    absent = max(0, working_days - total_check_ins)
    
    # Calculate average check-in time
    avg_time_result = await db.execute(
        select(func.avg(func.extract("hour", AttendanceLog.ts) * 60 + func.extract("minute", AttendanceLog.ts)))
        .where(
            and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.user_id == user_id,
                AttendanceLog.type == "check_in",
                AttendanceLog.status.in_(["on_time", "late"]),
                AttendanceLog.ts >= datetime.combine(from_date, time.min),
                AttendanceLog.ts <= datetime.combine(to_date, time.max),
            )
        )
    )
    avg_minutes = avg_time_result.scalar()
    
    avg_check_in_time = None
    if avg_minutes is not None:
        hours = int(avg_minutes) // 60
        minutes = int(avg_minutes) % 60
        avg_check_in_time = f"{hours:02d}:{minutes:02d}"
    
    # Calculate attendance rate
    attendance_rate = (total_check_ins / working_days * 100) if working_days > 0 else 0
    punctuality_rate = (on_time / total_check_ins * 100) if total_check_ins > 0 else 0
    
    return {
        "user_id": str(user_id),
        "user_name": user.name,
        "period": {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "working_days": working_days,
        },
        "summary": {
            "on_time": on_time,
            "late": late,
            "absent": absent,
            "total_check_ins": total_check_ins,
        },
        "rates": {
            "attendance_rate": round(attendance_rate, 2),
            "punctuality_rate": round(punctuality_rate, 2),
        },
        "average_check_in_time": avg_check_in_time,
    }


# Alias for frontend compatibility
@router.get("/users/{user_id}/stats")
async def get_user_stats(
    user_id: UUID,
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get attendance statistics for a user.
    Alias for /summary/user/{user_id} for frontend compatibility.
    
    Admin only.
    """
    # Default to last 30 days if not specified
    if not to_date:
        to_date = date.today()
    if not from_date:
        from_date = to_date - timedelta(days=30)
    
    return await get_user_summary(user_id, from_date, to_date, db, current_user)


@router.get("/daily-summaries")
async def get_daily_summaries(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get daily summaries for a date range.
    
    Admin only.
    """
    org_id = current_user.org_id
    
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
    
    # Generate daily summaries
    summaries = []
    current_date = start_date
    
    while current_date <= end_date:
        start = datetime.combine(current_date, time.min)
        end = datetime.combine(current_date, time.max)
        
        # Get status counts for the day
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
        
        summaries.append(
            DailySummary(
                date=current_date,
                total_users=total_users,
                checked_in=checked_in,
                on_time=on_time,
                late=late,
                absent=absent,
                unknown_attempts=unknown_attempts,
            ).model_dump()
        )
        
        current_date += timedelta(days=1)
    
    return summaries


@router.get("/export")
async def export_report(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    format: str = Query("csv", description="Export format (csv, xlsx, pdf)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Export attendance report in various formats.
    Currently supports CSV.
    
    Admin only.
    """
    # Delegate to CSV export - other formats can be added later
    return await export_attendance_csv(start_date, end_date, user_id, db, current_user)


@router.get("/weekly-trend")
async def get_weekly_trend(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get weekly attendance trend for the last 7 days.
    
    Admin only.
    """
    org_id = current_user.org_id
    today = date.today()
    
    trends = []
    
    for day_offset in range(6, -1, -1):
        current_date = today - timedelta(days=day_offset)
        start = datetime.combine(current_date, time.min)
        end = datetime.combine(current_date, time.max)
        
        # Get check-in count
        check_in_result = await db.execute(
            select(func.count(func.distinct(AttendanceLog.user_id))).where(
                and_(
                    AttendanceLog.org_id == org_id,
                    AttendanceLog.type == "check_in",
                    AttendanceLog.status.in_(["on_time", "late"]),
                    AttendanceLog.ts >= start,
                    AttendanceLog.ts <= end,
                )
            )
        )
        check_ins = check_in_result.scalar() or 0
        
        # Get check-out count
        check_out_result = await db.execute(
            select(func.count(func.distinct(AttendanceLog.user_id))).where(
                and_(
                    AttendanceLog.org_id == org_id,
                    AttendanceLog.type == "check_out",
                    AttendanceLog.ts >= start,
                    AttendanceLog.ts <= end,
                )
            )
        )
        check_outs = check_out_result.scalar() or 0
        
        trends.append({
            "date": current_date.isoformat(),
            "check_ins": check_ins,
            "check_outs": check_outs,
        })
    
    return trends


@router.get("/department-summary")
async def get_department_summary(
    target_date: Optional[date] = Query(None, description="Date for summary (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get department-wise attendance summary.
    
    Admin only.
    """
    org_id = current_user.org_id
    summary_date = target_date or date.today()
    start = datetime.combine(summary_date, time.min)
    end = datetime.combine(summary_date, time.max)
    
    # Get all departments in org
    departments_result = await db.execute(
        select(User.department, func.count(User.id))
        .where(
            and_(
                User.org_id == org_id,
                User.is_active == True,
            )
        )
        .group_by(User.department)
    )
    department_counts = {row[0] or "Unassigned": row[1] for row in departments_result.fetchall()}
    
    # Get present count per department
    present_result = await db.execute(
        select(User.department, func.count(func.distinct(AttendanceLog.user_id)))
        .join(AttendanceLog, AttendanceLog.user_id == User.id)
        .where(
            and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.type == "check_in",
                AttendanceLog.status.in_(["on_time", "late"]),
                AttendanceLog.ts >= start,
                AttendanceLog.ts <= end,
            )
        )
        .group_by(User.department)
    )
    present_counts = {row[0] or "Unassigned": row[1] for row in present_result.fetchall()}
    
    # Build summary
    summaries = []
    for dept, total in department_counts.items():
        present = present_counts.get(dept, 0)
        summaries.append({
            "department": dept,
            "present": present,
            "absent": max(0, total - present),
        })
    
    return summaries
