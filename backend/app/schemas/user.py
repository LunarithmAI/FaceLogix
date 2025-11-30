import base64
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


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


class FaceStatusResponse(BaseModel):
    """Schema for face enrollment status response."""
    
    has_face: bool
    embeddings_count: int
    enrolled_at: Optional[datetime] = None


class ResetPasswordRequest(BaseModel):
    """Schema for password reset request."""
    
    new_password: str = Field(..., min_length=8)


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
            # Handle data URI format: data:image/jpeg;base64,/9j/4AAQ...
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
