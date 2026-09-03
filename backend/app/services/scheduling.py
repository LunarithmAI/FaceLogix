from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_exception import CalendarException
from app.models.shift import Shift
from app.models.shift_assignment import UserShiftAssignment
from app.models.unit_assignment import UserUnitAssignment
from app.models.user import User


@dataclass(frozen=True, slots=True)
class ScheduleResolution:
    schedule_date: date
    unit_id: UUID | None
    shift_id: UUID | None
    shift: Shift | None
    scheduled: bool
    starts_at: datetime | None
    ends_at: datetime | None
    late_after: datetime | None
    early_before: datetime | None


def attendance_status(
    event_type: str,
    event_time: datetime,
    schedule: ScheduleResolution,
) -> str:
    if not schedule.scheduled:
        return "unscheduled"
    if event_type == "check_in":
        return (
            "late"
            if schedule.late_after is not None and event_time > schedule.late_after
            else "on_time"
        )
    return (
        "early_departure"
        if schedule.early_before is not None and event_time < schedule.early_before
        else "on_time"
    )


def _wall_time(
    target_date: date,
    target_time: time,
    zone: ZoneInfo,
    *,
    prefer_late_fold: bool,
) -> datetime:
    naive = datetime.combine(target_date, target_time)
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        round_trip = candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
        if round_trip == naive:
            candidates.append(candidate)
    if candidates:
        return candidates[-1 if prefer_late_fold else 0].astimezone(UTC)
    probe = naive
    for _ in range(180):
        probe += timedelta(minutes=1)
        candidate = probe.replace(tzinfo=zone, fold=0)
        if candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == probe:
            return candidate.astimezone(UTC)
    raise ValueError("local wall time could not be resolved across the DST transition")


async def _assignment_ids(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    schedule_date: date,
) -> tuple[UUID | None, UUID | None]:
    unit_id = await db.scalar(
        select(UserUnitAssignment.unit_id).where(
            UserUnitAssignment.org_id == org_id,
            UserUnitAssignment.user_id == user_id,
            UserUnitAssignment.effective_from <= schedule_date,
            or_(
                UserUnitAssignment.effective_to.is_(None),
                UserUnitAssignment.effective_to >= schedule_date,
            ),
        )
    )
    shift_id = await db.scalar(
        select(UserShiftAssignment.shift_id).where(
            UserShiftAssignment.org_id == org_id,
            UserShiftAssignment.user_id == user_id,
            UserShiftAssignment.effective_from <= schedule_date,
            or_(
                UserShiftAssignment.effective_to.is_(None),
                UserShiftAssignment.effective_to >= schedule_date,
            ),
        )
    )
    return unit_id, shift_id


async def _is_scheduled(
    db: AsyncSession,
    org_id: UUID,
    unit_id: UUID | None,
    shift: Shift,
    schedule_date: date,
) -> bool:
    exceptions = list(
        (
            await db.scalars(
                select(CalendarException)
                .where(
                    CalendarException.org_id == org_id,
                    CalendarException.exception_date == schedule_date,
                    or_(
                        CalendarException.unit_id == unit_id,
                        CalendarException.unit_id.is_(None),
                    ),
                )
                .order_by(CalendarException.unit_id.desc().nulls_last())
            )
        ).all()
    )
    unit_exception = next(
        (item for item in exceptions if unit_id is not None and item.unit_id == unit_id),
        None,
    )
    org_exception = next((item for item in exceptions if item.unit_id is None), None)
    exception = unit_exception or org_exception
    if exception is not None:
        return exception.kind == "working_day"
    return schedule_date.weekday() in shift.scheduled_weekdays


async def resolve_schedule_for_date(
    db: AsyncSession,
    *,
    org_id: UUID,
    timezone_name: str,
    user_id: UUID,
    schedule_date: date,
) -> ScheduleResolution:
    unit_id, shift_id = await _assignment_ids(db, org_id, user_id, schedule_date)
    shift = None
    if shift_id is not None:
        shift = await db.scalar(
            select(Shift).where(Shift.id == shift_id, Shift.org_id == org_id)
        )
    if shift is None:
        return ScheduleResolution(
            schedule_date=schedule_date,
            unit_id=unit_id,
            shift_id=shift_id,
            shift=None,
            scheduled=False,
            starts_at=None,
            ends_at=None,
            late_after=None,
            early_before=None,
        )
    zone = ZoneInfo(timezone_name)
    end_date = schedule_date + timedelta(days=shift.end_time <= shift.start_time)
    starts_at = _wall_time(schedule_date, shift.start_time, zone, prefer_late_fold=False)
    ends_at = _wall_time(end_date, shift.end_time, zone, prefer_late_fold=True)
    scheduled = await _is_scheduled(db, org_id, unit_id, shift, schedule_date)
    return ScheduleResolution(
        schedule_date=schedule_date,
        unit_id=unit_id,
        shift_id=shift.id,
        shift=shift,
        scheduled=scheduled,
        starts_at=starts_at,
        ends_at=ends_at,
        late_after=starts_at + timedelta(minutes=shift.late_grace_minutes),
        early_before=ends_at - timedelta(minutes=shift.early_departure_grace_minutes),
    )


async def resolve_schedule_for_event(
    db: AsyncSession,
    *,
    org_id: UUID,
    timezone_name: str,
    user_id: UUID,
    event_time: datetime,
) -> ScheduleResolution:
    aware_event = event_time if event_time.tzinfo is not None else event_time.replace(tzinfo=UTC)
    local_date = aware_event.astimezone(ZoneInfo(timezone_name)).date()
    previous = await resolve_schedule_for_date(
        db,
        org_id=org_id,
        timezone_name=timezone_name,
        user_id=user_id,
        schedule_date=local_date - timedelta(days=1),
    )
    if (
        previous.shift is not None
        and previous.shift.end_time <= previous.shift.start_time
        and previous.starts_at is not None
        and previous.ends_at is not None
        and previous.starts_at <= aware_event <= previous.ends_at
    ):
        return previous
    return await resolve_schedule_for_date(
        db,
        org_id=org_id,
        timezone_name=timezone_name,
        user_id=user_id,
        schedule_date=local_date,
    )

async def schedule_rows_for_date(
    db: AsyncSession,
    *,
    org_id: UUID,
    timezone_name: str,
    schedule_date: date,
    scope_unit_ids: set[UUID] | None = None,
    unit_id: UUID | None = None,
    shift_id: UUID | None = None,
) -> list[tuple[User, ScheduleResolution]]:
    conditions = [
        User.org_id == org_id,
        UserShiftAssignment.org_id == org_id,
        UserShiftAssignment.effective_from <= schedule_date,
        or_(
            UserShiftAssignment.effective_to.is_(None),
            UserShiftAssignment.effective_to >= schedule_date,
        ),
    ]
    if shift_id is not None:
        conditions.append(UserShiftAssignment.shift_id == shift_id)
    effective_units = select(UserUnitAssignment.user_id).where(
        UserUnitAssignment.org_id == org_id,
        UserUnitAssignment.effective_from <= schedule_date,
        or_(
            UserUnitAssignment.effective_to.is_(None),
            UserUnitAssignment.effective_to >= schedule_date,
        ),
    )
    if unit_id is not None:
        effective_units = effective_units.where(UserUnitAssignment.unit_id == unit_id)
        conditions.append(User.id.in_(effective_units))
    elif scope_unit_ids is not None:
        effective_units = effective_units.where(
            UserUnitAssignment.unit_id.in_(scope_unit_ids)
        )
        conditions.append(User.id.in_(effective_units))
    users = list(
        (
            await db.scalars(
                select(User)
                .join(
                    UserShiftAssignment,
                    UserShiftAssignment.user_id == User.id,
                )
                .where(*conditions)
                .order_by(User.name, User.id)
            )
        ).unique()
    )
    return [
        (
            user,
            await resolve_schedule_for_date(
                db,
                org_id=org_id,
                timezone_name=timezone_name,
                user_id=user.id,
                schedule_date=schedule_date,
            ),
        )
        for user in users
    ]
