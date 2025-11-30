from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
import re


class LoginRequest(BaseModel):
    """User login request."""
    
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format - permissive to allow .local domains for dev."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()


class LoginResponse(BaseModel):
    """User login response with tokens."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
    org_id: UUID
    role: str
    name: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    
    refresh_token: str


class RefreshResponse(BaseModel):
    """Token refresh response."""
    
    access_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    """Logout request."""
    
    refresh_token: str


class DeviceLoginRequest(BaseModel):
    """Device authentication request."""
    
    device_id: UUID
    device_secret: str


class DeviceLoginResponse(BaseModel):
    """Device authentication response."""
    
    device_token: str
    token_type: str = "bearer"
    org_id: UUID
    device_name: str


class TokenPayload(BaseModel):
    """JWT token payload."""
    
    sub: str  # Subject (user_id or device_id)
    exp: datetime
    type: str  # "access", "refresh", or "device"
    org: Optional[str] = None  # Organization ID for device tokens
    role: Optional[str] = None
    name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Password change request."""
    
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class UserProfileResponse(BaseModel):
    """Current user profile response."""
    
    id: UUID
    org_id: UUID
    email: Optional[str]
    name: str
    role: str
    department: Optional[str]
    is_active: bool
    enrolled_at: Optional[datetime]
    created_at: datetime
