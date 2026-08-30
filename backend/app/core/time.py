from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_day_bounds(
    timezone_name: str,
    instant: datetime | None = None,
) -> tuple[date, datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    current = instant or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    local_date = current.astimezone(zone).date()
    start, end = local_date_bounds(timezone_name, local_date)
    return local_date, start, end


def local_date_bounds(
    timezone_name: str,
    target_date: date,
) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_start = datetime.combine(target_date, time.min, tzinfo=zone)
    next_local_start = datetime.combine(
        target_date + timedelta(days=1),
        time.min,
        tzinfo=zone,
    )
    return (
        local_start.astimezone(UTC),
        next_local_start.astimezone(UTC),
    )


def local_time(timezone_name: str, instant: datetime) -> datetime:
    aware = instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)
    return aware.astimezone(ZoneInfo(timezone_name))
