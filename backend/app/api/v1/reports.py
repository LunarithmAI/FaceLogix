import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import require_operator
from app.api.tenant import load_org, load_user
from app.core.database import get_db
from app.core.time import local_date_bounds, local_day_bounds
from app.models.attendance_log import AttendanceLog
from app.models.device import Device
from app.models.org import Org
from app.models.user import User
from app.schemas.report import (
    AttendanceCounts,
    AttendanceRates,
    DashboardStats,
    DashboardToday,
    DepartmentSummary,
    RecentActivity,
    ReportDailySummary,
    ReportPeriod,
    UserAttendanceStats,
    WeeklyTrendPoint,
)

router = APIRouter(prefix="/reports", tags=["Reports"])
MAX_REPORT_DAYS = 366


def validate_range(from_date: date, to_date: date) -> None:
    span = (to_date - from_date).days + 1
    if span < 1:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_DATE_RANGE",
                "message": "from_date must not exceed to_date",
            },
        )
    if span > MAX_REPORT_DAYS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "DATE_RANGE_TOO_LARGE",
                "message": "Report ranges may include at most 366 days",
            },
        )


def working_day_count(from_date: date, to_date: date) -> int:
    return sum(
        1
        for offset in range((to_date - from_date).days + 1)
        if (from_date + timedelta(days=offset)).weekday() < 5
    )


def format_average_minutes(average_minutes: Decimal | float | None) -> str | None:
    if average_minutes is None:
        return None
    minutes = int(average_minutes)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def local_date_expression(timezone_name: str) -> ColumnElement[date]:
    return cast(func.timezone(timezone_name, AttendanceLog.ts), Date)


async def grouped_daily_counts(
    db: AsyncSession,
    org: Org,
    from_date: date,
    to_date: date,
) -> dict[date, dict[str, int]]:
    range_start, _ = local_date_bounds(org.timezone, from_date)
    _, range_end = local_date_bounds(org.timezone, to_date)
    local_date = local_date_expression(org.timezone).label("local_date")
    rows = (
        await db.execute(
            select(
                local_date,
                AttendanceLog.type,
                AttendanceLog.status,
                func.count(func.distinct(AttendanceLog.user_id)),
            )
            .where(
                AttendanceLog.org_id == org.id,
                AttendanceLog.ts >= range_start,
                AttendanceLog.ts < range_end,
            )
            .group_by(local_date, AttendanceLog.type, AttendanceLog.status)
        )
    ).all()
    counts: dict[date, dict[str, int]] = {}
    for local_day, attendance_type, attendance_status, count in rows:
        key = f"{attendance_type}:{attendance_status}"
        counts.setdefault(local_day, {})[key] = int(count)
    return counts


def report_daily_summary(
    day: date,
    total_users: int,
    counts: dict[str, int],
) -> ReportDailySummary:
    on_time = counts.get("check_in:on_time", 0)
    late = counts.get("check_in:late", 0)
    check_ins = on_time + late
    check_outs = sum(
        count
        for key, count in counts.items()
        if key.startswith("check_out:") and key != "check_out:unknown_user"
    )
    return ReportDailySummary(
        date=day,
        total_users=total_users,
        check_ins=check_ins,
        check_outs=check_outs,
        on_time=on_time,
        late=late,
        absent=max(0, total_users - check_ins),
        unknown_attempts=counts.get("check_in:unknown_user", 0),
        on_time_percentage=round(on_time / check_ins * 100 if check_ins else 0, 2),
    )


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> DashboardStats:
    org = await load_org(db, current_user.org_id)
    today, day_start, day_end = local_day_bounds(org.timezone)
    total_users = (
        await db.scalar(
            select(func.count(User.id)).where(
                User.org_id == org.id,
                User.is_active.is_(True),
            )
        )
        or 0
    )
    active_devices = (
        await db.scalar(
            select(func.count(Device.id)).where(
                Device.org_id == org.id,
                Device.is_active.is_(True),
            )
        )
        or 0
    )
    pending_enrollments = (
        await db.scalar(
            select(func.count(User.id)).where(
                User.org_id == org.id,
                User.is_active.is_(True),
                User.enrolled_at.is_(None),
            )
        )
        or 0
    )
    status_rows = (
        await db.execute(
            select(
                AttendanceLog.status,
                func.count(func.distinct(AttendanceLog.user_id)),
            )
            .where(
                AttendanceLog.org_id == org.id,
                AttendanceLog.type == "check_in",
                AttendanceLog.ts >= day_start,
                AttendanceLog.ts < day_end,
            )
            .group_by(AttendanceLog.status)
        )
    ).all()
    status_counts = {row[0]: int(row[1]) for row in status_rows}
    checked_out = (
        await db.scalar(
            select(func.count(func.distinct(AttendanceLog.user_id))).where(
                AttendanceLog.org_id == org.id,
                AttendanceLog.type == "check_out",
                AttendanceLog.ts >= day_start,
                AttendanceLog.ts < day_end,
            )
        )
        or 0
    )
    local_timestamp = func.timezone(org.timezone, AttendanceLog.ts)
    average_rows = (
        await db.execute(
            select(
                AttendanceLog.type,
                func.avg(
                    func.extract("hour", local_timestamp) * 60
                    + func.extract("minute", local_timestamp)
                ),
            )
            .where(
                AttendanceLog.org_id == org.id,
                AttendanceLog.ts >= day_start,
                AttendanceLog.ts < day_end,
                AttendanceLog.status.in_(["on_time", "late", "early"]),
            )
            .group_by(AttendanceLog.type)
        )
    ).all()
    average_times = {
        attendance_type: format_average_minutes(average_minutes)
        for attendance_type, average_minutes in average_rows
    }
    recent_rows = (
        await db.execute(
            select(
                AttendanceLog.id,
                AttendanceLog.ts,
                AttendanceLog.type,
                AttendanceLog.status,
                AttendanceLog.confidence_score,
                User.id.label("user_id"),
                User.name.label("user_name"),
                Device.id.label("device_id"),
                Device.name.label("device_name"),
            )
            .outerjoin(User, AttendanceLog.user_id == User.id)
            .outerjoin(Device, AttendanceLog.device_id == Device.id)
            .where(AttendanceLog.org_id == org.id)
            .order_by(AttendanceLog.ts.desc())
            .limit(10)
        )
    ).all()
    recent_activity = [
        RecentActivity(
            id=row.id,
            timestamp=row.ts,
            type=row.type,
            status=row.status,
            confidence_score=row.confidence_score,
            user_id=row.user_id,
            user_name=row.user_name,
            device_id=row.device_id,
            device_name=row.device_name,
        )
        for row in recent_rows
    ]
    on_time = status_counts.get("on_time", 0)
    late = status_counts.get("late", 0)
    checked_in = on_time + late
    return DashboardStats(
        today=DashboardToday(
            date=today,
            total_employees=total_users,
            checked_in=checked_in,
            checked_out=checked_out,
            on_time=on_time,
            late_arrivals=late,
            absent=max(0, total_users - checked_in),
            average_check_in_time=average_times.get("check_in"),
            average_check_out_time=average_times.get("check_out"),
        ),
        total_users=total_users,
        active_devices=active_devices,
        pending_enrollments=pending_enrollments,
        recent_activity=recent_activity,
    )


@router.get("/users/{user_id}/stats", response_model=UserAttendanceStats)
async def get_user_stats(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
) -> UserAttendanceStats:
    org = await load_org(db, current_user.org_id)
    user = await load_user(db, org.id, user_id)
    local_today = local_day_bounds(org.timezone)[0]
    effective_to = to_date or local_today
    effective_from = from_date or effective_to - timedelta(days=29)
    validate_range(effective_from, effective_to)
    range_start, _ = local_date_bounds(org.timezone, effective_from)
    _, range_end = local_date_bounds(org.timezone, effective_to)
    conditions = (
        AttendanceLog.org_id == org.id,
        AttendanceLog.user_id == user.id,
        AttendanceLog.type == "check_in",
        AttendanceLog.ts >= range_start,
        AttendanceLog.ts < range_end,
    )
    rows = (
        await db.execute(
            select(AttendanceLog.status, func.count(AttendanceLog.id))
            .where(*conditions)
            .group_by(AttendanceLog.status)
        )
    ).all()
    counts = {row[0]: int(row[1]) for row in rows}
    on_time = counts.get("on_time", 0)
    late = counts.get("late", 0)
    total_check_ins = on_time + late
    working_days = working_day_count(effective_from, effective_to)
    local_timestamp = func.timezone(org.timezone, AttendanceLog.ts)
    average_minutes = await db.scalar(
        select(
            func.avg(
                func.extract("hour", local_timestamp) * 60 + func.extract("minute", local_timestamp)
            )
        ).where(
            *conditions,
            AttendanceLog.status.in_(["on_time", "late"]),
        )
    )
    average_check_in_time = format_average_minutes(average_minutes)
    return UserAttendanceStats(
        user_id=user.id,
        user_name=user.name,
        period=ReportPeriod(
            from_date=effective_from,
            to_date=effective_to,
            working_days=working_days,
        ),
        summary=AttendanceCounts(
            on_time=on_time,
            late=late,
            absent=max(0, working_days - total_check_ins),
            total_check_ins=total_check_ins,
        ),
        rates=AttendanceRates(
            attendance_rate=round(
                total_check_ins / working_days * 100 if working_days else 0,
                2,
            ),
            punctuality_rate=round(
                on_time / total_check_ins * 100 if total_check_ins else 0,
                2,
            ),
        ),
        average_check_in_time=average_check_in_time,
    )


@router.get("/daily-summaries", response_model=list[ReportDailySummary])
async def get_daily_summaries(
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> list[ReportDailySummary]:
    validate_range(from_date, to_date)
    org = await load_org(db, current_user.org_id)
    total_users = (
        await db.scalar(
            select(func.count(User.id)).where(
                User.org_id == org.id,
                User.is_active.is_(True),
            )
        )
        or 0
    )
    counts_by_day = await grouped_daily_counts(db, org, from_date, to_date)
    return [
        report_daily_summary(day, total_users, counts_by_day.get(day, {}))
        for day_offset in range((to_date - from_date).days + 1)
        for day in [from_date + timedelta(days=day_offset)]
    ]


def safe_csv_cell(value: object) -> str:
    text_value = "" if value is None else str(value)
    return f"'{text_value}" if text_value.startswith(("=", "+", "-", "@")) else text_value


@router.get("/export")
async def export_report(
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    user_id: Annotated[UUID | None, Query()] = None,
    format: Annotated[Literal["csv"], Query()] = "csv",
) -> Response:
    del format
    validate_range(from_date, to_date)
    org = await load_org(db, current_user.org_id)
    range_start, _ = local_date_bounds(org.timezone, from_date)
    _, range_end = local_date_bounds(org.timezone, to_date)
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
            AttendanceLog.org_id == org.id,
            AttendanceLog.ts >= range_start,
            AttendanceLog.ts < range_end,
        )
        .order_by(AttendanceLog.ts.desc())
    )
    if user_id is not None:
        query = query.where(AttendanceLog.user_id == user_id)
    rows = (await db.execute(query)).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Name",
            "Email",
            "External ID",
            "Department",
            "Timestamp",
            "Type",
            "Status",
            "Confidence",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                safe_csv_cell(row.id),
                safe_csv_cell(row.name),
                safe_csv_cell(row.email),
                safe_csv_cell(row.external_id),
                safe_csv_cell(row.department),
                row.ts.isoformat(),
                row.type,
                row.status,
                "" if row.confidence_score is None else f"{row.confidence_score:.4f}",
            ]
        )
    filename = f"attendance_{from_date}_{to_date}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/weekly-trend", response_model=list[WeeklyTrendPoint])
async def get_weekly_trend(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> list[WeeklyTrendPoint]:
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    from_date = today - timedelta(days=6)
    range_start, _ = local_date_bounds(org.timezone, from_date)
    _, range_end = local_date_bounds(org.timezone, today)
    local_date = local_date_expression(org.timezone).label("local_date")
    rows = (
        await db.execute(
            select(
                local_date,
                AttendanceLog.type,
                func.count(func.distinct(AttendanceLog.user_id)),
            )
            .where(
                AttendanceLog.org_id == org.id,
                AttendanceLog.ts >= range_start,
                AttendanceLog.ts < range_end,
                AttendanceLog.status != "unknown_user",
            )
            .group_by(local_date, AttendanceLog.type)
        )
    ).all()
    counts = {(row[0], row[1]): int(row[2]) for row in rows}
    return [
        WeeklyTrendPoint(
            date=day,
            check_ins=counts.get((day, "check_in"), 0),
            check_outs=counts.get((day, "check_out"), 0),
        )
        for offset in range(7)
        for day in [from_date + timedelta(days=offset)]
    ]


@router.get("/department-summary", response_model=list[DepartmentSummary])
async def get_department_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    target_date: Annotated[date | None, Query()] = None,
) -> list[DepartmentSummary]:
    org = await load_org(db, current_user.org_id)
    local_today, today_start, today_end = local_day_bounds(org.timezone)
    if target_date is None:
        day_start, day_end = today_start, today_end
    else:
        day_start, day_end = local_date_bounds(org.timezone, target_date)
    department_rows = (
        await db.execute(
            select(User.department, func.count(User.id))
            .where(User.org_id == org.id, User.is_active.is_(True))
            .group_by(User.department)
        )
    ).all()
    department_counts = {row[0] or "Unassigned": int(row[1]) for row in department_rows}
    present_rows = (
        await db.execute(
            select(User.department, func.count(func.distinct(AttendanceLog.user_id)))
            .join(AttendanceLog, AttendanceLog.user_id == User.id)
            .where(
                AttendanceLog.org_id == org.id,
                AttendanceLog.type == "check_in",
                AttendanceLog.status.in_(["on_time", "late"]),
                AttendanceLog.ts >= day_start,
                AttendanceLog.ts < day_end,
            )
            .group_by(User.department)
        )
    ).all()
    present_counts = {row[0] or "Unassigned": int(row[1]) for row in present_rows}
    return [
        DepartmentSummary(
            department=department,
            present=present_counts.get(department, 0),
            absent=max(0, total - present_counts.get(department, 0)),
        )
        for department, total in sorted(department_counts.items())
    ]
