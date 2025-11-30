from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    """Schema for check-in/check-out request."""
    
    device_id: Optional[UUID] = None  # Optional if using device token


class CheckInResponse(BaseModel):
    """Schema for check-in/check-out response."""
    
    success: bool
    status: str  # "on_time", "late", "unknown_user", "already_checked_in", "no_face_detected"
    message: str
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    check_in_time: Optional[datetime] = None
    confidence_score: Optional[float] = None


class AttendanceLogResponse(BaseModel):
    """Schema for attendance log response."""
    
    id: UUID
    user_id: Optional[UUID]
    user_name: Optional[str] = None
    device_id: Optional[UUID]
    device_name: Optional[str] = None
    ts: datetime
    type: str  # "check_in", "check_out"
    status: str  # "on_time", "late", "early", "unknown_user"
    confidence_score: Optional[float]

    class Config:
        from_attributes = True


class AttendanceQuery(BaseModel):
    """Schema for querying attendance logs."""
    
    user_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    type: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class DailySummary(BaseModel):
    """Schema for daily attendance summary."""
    
    date: date
    total_users: int
    checked_in: int
    on_time: int
    late: int
    absent: int
    unknown_attempts: int
