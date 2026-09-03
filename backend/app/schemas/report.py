from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.unit import UnitSummary as UnitDefinitionSummary


class RecentActivity(BaseModel):
    id: UUID
    timestamp: datetime
    type: str
    status: str
    confidence_score: float | None
    user_id: UUID | None
    user_name: str | None
    device_id: UUID | None
    device_name: str | None


class DashboardToday(BaseModel):
    date: date
    total_employees: int
    checked_in: int
    checked_out: int
    on_time: int
    late_arrivals: int
    absent: int
    average_check_in_time: str | None
    average_check_out_time: str | None


class DashboardStats(BaseModel):
    today: DashboardToday
    total_users: int
    active_devices: int
    pending_enrollments: int
    recent_activity: list[RecentActivity]


class ReportDailySummary(BaseModel):
    date: date
    total_users: int
    check_ins: int
    check_outs: int
    on_time: int
    late: int
    absent: int
    unknown_attempts: int
    on_time_percentage: float


class ReportPeriod(BaseModel):
    from_date: date
    to_date: date
    working_days: int


class AttendanceCounts(BaseModel):
    on_time: int
    late: int
    absent: int
    total_check_ins: int


class AttendanceRates(BaseModel):
    attendance_rate: float
    punctuality_rate: float


class UserAttendanceStats(BaseModel):
    user_id: UUID
    user_name: str
    period: ReportPeriod
    summary: AttendanceCounts
    rates: AttendanceRates
    average_check_in_time: str | None


class WeeklyTrendPoint(BaseModel):
    date: date
    check_ins: int
    check_outs: int


class UnitSummary(BaseModel):
    unit: UnitDefinitionSummary
    scheduled_person_days: int
    present_person_days: int
    absent_person_days: int
    on_time: int
    late: int
    attendance_rate: float
