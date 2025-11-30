from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    external_id: Optional[str] = Field(None, max_length=255)
    role: str = Field(default="member", pattern="^(admin|manager|member)$")
    department: Optional[str] = Field(None, max_length=255)


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    external_id: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, pattern="^(admin|manager|member)$")
    department: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response."""
    
    id: UUID
    org_id: UUID
    email: Optional[str]
    name: str
    external_id: Optional[str]
    role: str
    department: Optional[str]
    is_active: bool
    enrolled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserEnrollResponse(BaseModel):
    """Schema for user enrollment response with face data."""
    
    user_id: UUID
    embeddings_count: int
    enrolled_at: datetime
