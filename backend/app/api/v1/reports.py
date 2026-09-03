import csv
import io
from collections import defaultdict
from datetime import date, timedelta
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import ensure_user_in_scope, managed_unit_ids, require_operator
from app.api.tenant import load_org, load_user
from app.core.database import get_db
from app.core.identity import UserRole
from app.core.time import local_day_bounds
from app.models.attendance_log import AttendanceLog
from app.models.device import Device
from app.models.org import Org
from app.models.organizational_unit import OrganizationalUnit
from app.models.shift import Shift
from app.models.user import User
from app.schemas.report import (
    AttendanceCounts,
    AttendanceRates,
    DashboardStats,
    DashboardToday,
    RecentActivity,
    ReportDailySummary,
    ReportPeriod,
    UserAttendanceStats,
    WeeklyTrendPoint,
)
from app.schemas.report import (
    UnitSummary as UnitReportSummary,
)
from app.schemas.unit import UnitSummary
from app.services.attendance_records import effective_attendance_condition
from app.services.scheduling import ScheduleResolution, schedule_rows_for_date

router = APIRouter(prefix="/reports", tags=["Reports"])
MAX_REPORT_DAYS = 366


async def operator_scope_ids(db: AsyncSession, actor: User) -> set[UUID] | None:
    if actor.role != UserRole.MANAGER.value:
        return None
    return await managed_unit_ids(db, actor)


def validate_range(from_date: date, to_date: date) -> None:
    span = (to_date - from_date).days + 1
    if span < 1:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_DATE_RANGE", "message": "from_date must not exceed to_date"},
        )
    if span > MAX_REPORT_DAYS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "DATE_RANGE_TOO_LARGE",
                "message": "Report ranges may include at most 366 days",
            },
        )


def days_in_range(from_date: date, to_date: date) -> list[date]:
    return [
        from_date + timedelta(days=offset)
        for offset in range((to_date - from_date).days + 1)
    ]


def log_scope_conditions(scope_ids: set[UUID] | None) -> list[ColumnElement[bool]]:
    return [] if scope_ids is None else [AttendanceLog.unit_id.in_(scope_ids)]


async def schedule_rows(
    db: AsyncSession,
    org: Org,
    day: date,
    scope_ids: set[UUID] | None,
) -> list[tuple[User, ScheduleResolution]]:
    return await schedule_rows_for_date(
        db,
        org_id=org.id,
        timezone_name=org.timezone,
        schedule_date=day,
        scope_unit_ids=scope_ids,
    )


async def effective_logs(
    db: AsyncSession,
    org_id: UUID,
    from_date: date,
    to_date: date,
    scope_ids: set[UUID] | None,
    *,
    user_id: UUID | None = None,
) -> list[AttendanceLog]:
    conditions = [
        AttendanceLog.org_id == org_id,
        AttendanceLog.schedule_date >= from_date,
        AttendanceLog.schedule_date <= to_date,
        effective_attendance_condition(),
        *log_scope_conditions(scope_ids),
    ]
    if user_id is not None:
        conditions.append(AttendanceLog.user_id == user_id)
    return list(
        (
            await db.scalars(
                select(AttendanceLog)
                .where(*conditions)
                .order_by(AttendanceLog.schedule_date, AttendanceLog.ts, AttendanceLog.id)
            )
        ).all()
    )


def average_local_time(logs: list[AttendanceLog], timezone_name: str) -> str | None:
    if not logs:
        return None
    zone = ZoneInfo(timezone_name)
    minutes = [log.ts.astimezone(zone).hour * 60 + log.ts.astimezone(zone).minute for log in logs]
    average = sum(minutes) // len(minutes)
    return f"{average // 60:02d}:{average % 60:02d}"


async def daily_summary(
    db: AsyncSession,
    org: Org,
    day: date,
    scope_ids: set[UUID] | None,
    logs: list[AttendanceLog] | None = None,
) -> ReportDailySummary:
    schedules = await schedule_rows(db, org, day, scope_ids)
    scheduled_ids = {user.id for user, schedule in schedules if schedule.scheduled}
    day_logs = logs if logs is not None else await effective_logs(db, org.id, day, day, scope_ids)
    check_ins = {
        log.user_id: log
        for log in day_logs
        if log.type == "check_in" and log.user_id in scheduled_ids
    }
    on_time = sum(log.status == "on_time" for log in check_ins.values())
    late = sum(log.status == "late" for log in check_ins.values())
    scheduled = len(scheduled_ids)
    present = len(check_ins)
    return ReportDailySummary(
        date=day,
        total_users=scheduled,
        check_ins=present,
        check_outs=len(
            {
                log.user_id
                for log in day_logs
                if log.type == "check_out" and log.user_id in scheduled_ids
            }
        ),
        on_time=on_time,
        late=late,
        absent=max(0, scheduled - present),
        unknown_attempts=sum(log.status == "unknown_user" for log in day_logs),
        on_time_percentage=round(on_time / present * 100 if present else 0, 2),
    )


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> DashboardStats:
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    scope_ids = await operator_scope_ids(db, current_user)
    logs = await effective_logs(db, org.id, today, today, scope_ids)
    summary = await daily_summary(db, org, today, scope_ids, logs)
    active_devices = await db.scalar(
        select(func.count(Device.id)).where(
            Device.org_id == org.id,
            Device.is_active.is_(True),
        )
    ) or 0
    scoped_user_ids = {
        user.id for user, _ in await schedule_rows(db, org, today, scope_ids)
    }
    pending_conditions = [
        User.org_id == org.id,
        User.is_active.is_(True),
        User.enrolled_at.is_(None),
    ]
    if scope_ids is not None:
        pending_conditions.append(User.id.in_(scoped_user_ids))
    pending_enrollments = await db.scalar(
        select(func.count(User.id)).where(*pending_conditions)
    ) or 0
    recent_rows = (
        await db.execute(
            select(
                AttendanceLog,
                User.name.label("user_name"),
                Device.name.label("device_name"),
            )
            .outerjoin(User, AttendanceLog.user_id == User.id)
            .outerjoin(Device, AttendanceLog.device_id == Device.id)
            .where(
                AttendanceLog.org_id == org.id,
                effective_attendance_condition(),
                *log_scope_conditions(scope_ids),
            )
            .order_by(AttendanceLog.ts.desc())
            .limit(10)
        )
    ).all()
    check_in_logs = [
        log for log in logs if log.type == "check_in" and log.status in {"on_time", "late"}
    ]
    check_out_logs = [
        log
        for log in logs
        if log.type == "check_out" and log.status in {"on_time", "early_departure"}
    ]
    return DashboardStats(
        today=DashboardToday(
            date=today,
            total_employees=summary.total_users,
            checked_in=summary.check_ins,
            checked_out=summary.check_outs,
            on_time=summary.on_time,
            late_arrivals=summary.late,
            absent=summary.absent,
            average_check_in_time=average_local_time(check_in_logs, org.timezone),
            average_check_out_time=average_local_time(check_out_logs, org.timezone),
        ),
        total_users=summary.total_users,
        active_devices=active_devices,
        pending_enrollments=pending_enrollments,
        recent_activity=[
            RecentActivity(
                id=row[0].id,
                timestamp=row[0].ts,
                type=row[0].type,
                status=row[0].status,
                confidence_score=row[0].confidence_score,
                user_id=row[0].user_id,
                user_name=row[1],
                device_id=row[0].device_id,
                device_name=row[2],
            )
            for row in recent_rows
        ],
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
    await ensure_user_in_scope(db, current_user, user)
    effective_to = to_date or local_day_bounds(org.timezone)[0]
    effective_from = from_date or effective_to - timedelta(days=29)
    validate_range(effective_from, effective_to)
    scope_ids = await operator_scope_ids(db, current_user)
    scheduled_days = 0
    for day in days_in_range(effective_from, effective_to):
        rows = await schedule_rows(db, org, day, scope_ids)
        scheduled_days += any(
            row_user.id == user.id and schedule.scheduled for row_user, schedule in rows
        )
    logs = await effective_logs(
        db,
        org.id,
        effective_from,
        effective_to,
        scope_ids,
        user_id=user.id,
    )
    check_ins = [
        log for log in logs if log.type == "check_in" and log.status in {"on_time", "late"}
    ]
    on_time = sum(log.status == "on_time" for log in check_ins)
    late = sum(log.status == "late" for log in check_ins)
    present_days = len({log.schedule_date for log in check_ins})
    return UserAttendanceStats(
        user_id=user.id,
        user_name=user.name,
        period=ReportPeriod(
            from_date=effective_from,
            to_date=effective_to,
            working_days=scheduled_days,
        ),
        summary=AttendanceCounts(
            on_time=on_time,
            late=late,
            absent=max(0, scheduled_days - present_days),
            total_check_ins=len(check_ins),
        ),
        rates=AttendanceRates(
            attendance_rate=round(
                present_days / scheduled_days * 100 if scheduled_days else 0,
                2,
            ),
            punctuality_rate=round(on_time / len(check_ins) * 100 if check_ins else 0, 2),
        ),
        average_check_in_time=average_local_time(check_ins, org.timezone),
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
    scope_ids = await operator_scope_ids(db, current_user)
    logs = await effective_logs(db, org.id, from_date, to_date, scope_ids)
    logs_by_day: dict[date, list[AttendanceLog]] = defaultdict(list)
    for log in logs:
        if log.schedule_date is not None:
            logs_by_day[log.schedule_date].append(log)
    return [
        await daily_summary(db, org, day, scope_ids, logs_by_day[day])
        for day in days_in_range(from_date, to_date)
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
    scope_ids = await operator_scope_ids(db, current_user)
    if user_id is not None:
        target = await load_user(db, org.id, user_id)
        await ensure_user_in_scope(db, current_user, target)
    conditions = [
        AttendanceLog.org_id == org.id,
        AttendanceLog.schedule_date >= from_date,
        AttendanceLog.schedule_date <= to_date,
        effective_attendance_condition(),
        *log_scope_conditions(scope_ids),
    ]
    if user_id is not None:
        conditions.append(AttendanceLog.user_id == user_id)
    rows = (
        await db.execute(
            select(
                AttendanceLog,
                User.name.label("user_name"),
                User.email,
                User.external_id,
                OrganizationalUnit.name.label("unit_name"),
                OrganizationalUnit.kind.label("unit_kind"),
                Shift.name.label("shift_name"),
            )
            .outerjoin(User, AttendanceLog.user_id == User.id)
            .outerjoin(OrganizationalUnit, AttendanceLog.unit_id == OrganizationalUnit.id)
            .outerjoin(Shift, AttendanceLog.shift_id == Shift.id)
            .where(*conditions)
            .order_by(AttendanceLog.schedule_date.desc(), AttendanceLog.ts.desc())
        )
    ).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Name",
            "Email",
            "External ID",
            "Unit",
            "Unit Kind",
            "Shift",
            "Schedule Date",
            "Event Time",
            "Type",
            "Status",
            "Source",
            "Confidence",
            "Correction Reason",
            "Supersedes ID",
        ]
    )
    for row in rows:
        log = row[0]
        writer.writerow(
            [
                safe_csv_cell(log.id),
                safe_csv_cell(row.user_name),
                safe_csv_cell(row.email),
                safe_csv_cell(row.external_id),
                safe_csv_cell(row.unit_name),
                safe_csv_cell(row.unit_kind),
                safe_csv_cell(row.shift_name),
                log.schedule_date,
                log.ts.isoformat(),
                log.type,
                log.status,
                log.source,
                "" if log.confidence_score is None else f"{log.confidence_score:.4f}",
                safe_csv_cell(log.correction_reason),
                safe_csv_cell(log.supersedes_id),
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
    scope_ids = await operator_scope_ids(db, current_user)
    today = local_day_bounds(org.timezone)[0]
    from_date = today - timedelta(days=6)
    logs = await effective_logs(db, org.id, from_date, today, scope_ids)
    return [
        WeeklyTrendPoint(
            date=day,
            check_ins=len(
                {
                    log.user_id
                    for log in logs
                    if log.schedule_date == day
                    and log.type == "check_in"
                    and log.user_id is not None
                }
            ),
            check_outs=len(
                {
                    log.user_id
                    for log in logs
                    if log.schedule_date == day
                    and log.type == "check_out"
                    and log.user_id is not None
                }
            ),
        )
        for day in days_in_range(from_date, today)
    ]


@router.get("/unit-summary", response_model=list[UnitReportSummary])
async def get_unit_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
) -> list[UnitReportSummary]:
    org = await load_org(db, current_user.org_id)
    end = to_date or local_day_bounds(org.timezone)[0]
    start = from_date or end
    validate_range(start, end)
    scope_ids = await operator_scope_ids(db, current_user)
    unit_conditions = [OrganizationalUnit.org_id == org.id]
    if scope_ids is not None:
        unit_conditions.append(OrganizationalUnit.id.in_(scope_ids))
    units = list(
        (
            await db.scalars(
                select(OrganizationalUnit)
                .where(*unit_conditions)
                .order_by(OrganizationalUnit.name)
            )
        ).all()
    )
    scheduled: dict[UUID, int] = defaultdict(int)
    for day in days_in_range(start, end):
        for _, schedule in await schedule_rows(db, org, day, scope_ids):
            if schedule.scheduled and schedule.unit_id is not None:
                scheduled[schedule.unit_id] += 1
    logs = await effective_logs(db, org.id, start, end, scope_ids)
    present: dict[UUID, int] = defaultdict(int)
    on_time: dict[UUID, int] = defaultdict(int)
    late: dict[UUID, int] = defaultdict(int)
    seen: set[tuple[UUID, UUID | None, date | None]] = set()
    for log in logs:
        unit_id = log.unit_id
        if (
            log.type != "check_in"
            or unit_id is None
            or log.status not in {"on_time", "late"}
        ):
            continue
        key = (unit_id, log.user_id, log.schedule_date)
        if key in seen:
            continue
        seen.add(key)
        present[unit_id] += 1
        if log.status == "on_time":
            on_time[unit_id] += 1
        else:
            late[unit_id] += 1
    return [
        UnitReportSummary(
            unit=UnitSummary.model_validate(unit),
            scheduled_person_days=scheduled[unit.id],
            present_person_days=present[unit.id],
            absent_person_days=max(0, scheduled[unit.id] - present[unit.id]),
            on_time=on_time[unit.id],
            late=late[unit.id],
            attendance_rate=round(
                present[unit.id] / scheduled[unit.id] * 100 if scheduled[unit.id] else 0,
                2,
            ),
        )
        for unit in units
        if scheduled[unit.id] or present[unit.id]
    ]
