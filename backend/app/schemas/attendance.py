import base64
import re
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CheckInRequest(BaseModel):
    """Schema for check-in/check-out request with base64 image."""
    
    image: str = Field(..., description="Base64 encoded image (with or without data URI prefix)")
    device_id: Optional[UUID] = None
    timestamp: Optional[datetime] = None  # Frontend sends this but we use server time
    
    @field_validator('image')
    @classmethod
    def validate_and_extract_base64(cls, v: str) -> str:
        """Validate and extract base64 data from data URI or raw base64."""
        if not v:
            raise ValueError("Image data is required")
        
        # Handle data URI format: data:image/jpeg;base64,/9j/4AAQ...
        if v.startswith('data:'):
            match = re.match(r'data:image/[^;]+;base64,(.+)', v)
            if match:
                return match.group(1)
            raise ValueError("Invalid data URI format")
        
        # Assume raw base64
        return v
    
    def get_image_bytes(self) -> bytes:
        """Decode base64 image to bytes."""
        try:
            return base64.b64decode(self.image)
        except Exception as e:
            raise ValueError(f"Invalid base64 image data: {e}")


class FaceEnrollmentRequest(BaseModel):
    """Schema for face enrollment request with base64 images."""
    
    images: List[str] = Field(..., min_length=1, max_length=5, description="List of base64 encoded images")
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v: List[str]) -> List[str]:
        """Validate and extract base64 data from each image."""
        result = []
        for img in v:
            if not img:
                continue
            # Handle data URI format
            if img.startswith('data:'):
                match = re.match(r'data:image/[^;]+;base64,(.+)', img)
                if match:
                    result.append(match.group(1))
                else:
                    raise ValueError("Invalid data URI format in images")
            else:
                result.append(img)
        
        if not result:
            raise ValueError("At least one valid image is required")
        return result
    
    def get_image_bytes_list(self) -> List[bytes]:
        """Decode all base64 images to bytes."""
        result = []
        for img in self.images:
            try:
                result.append(base64.b64decode(img))
            except Exception as e:
                raise ValueError(f"Invalid base64 image data: {e}")
        return result


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
