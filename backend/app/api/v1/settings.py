"""
Settings API endpoints for organization and system configuration.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin
from app.core.config import settings
from app.models.device import Device
from app.models.org import Org
from app.models.user import User


router = APIRouter(prefix="/settings", tags=["settings"])


# ============================================================================
# Schemas
# ============================================================================

class OrgSettingsData(BaseModel):
    """Organization settings data stored in JSONB."""
    work_start_time: Optional[str] = Field(None, description="Work start time (HH:MM)")
    work_end_time: Optional[str] = Field(None, description="Work end time (HH:MM)")
    late_threshold_minutes: Optional[int] = Field(None, ge=0, le=120)
    require_liveness: Optional[bool] = None
    allow_remote_checkin: Optional[bool] = None
    face_match_threshold: Optional[float] = Field(None, ge=0.3, le=0.95)


class OrgSettingsResponse(BaseModel):
    """Organization settings response."""
    id: uuid.UUID
    name: str
    slug: str
    timezone: str
    is_active: bool
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrgSettingsUpdate(BaseModel):
    """Organization settings update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(None, max_length=50)
    settings: Optional[OrgSettingsData] = None


class SystemInfoResponse(BaseModel):
    """System information response."""
    version: str
    environment: str
    face_service_status: str  # online, offline, unknown
    database_status: str  # connected, disconnected
    total_users: int
    total_devices: int
    uptime_hours: float


class FaceServiceTestResponse(BaseModel):
    """Face service test response."""
    status: str
    latency_ms: float


# Track server start time
_server_start_time = datetime.utcnow()


# ============================================================================
# Organization Settings Endpoints
# ============================================================================

@router.get("/org", response_model=OrgSettingsResponse)
async def get_org_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current organization settings.
    Available to all authenticated users.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with an organization",
        )
    
    org = await db.get(Org, current_user.org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    return OrgSettingsResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        timezone=org.timezone,
        is_active=org.is_active,
        settings=org.settings or {},
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.patch("/org", response_model=OrgSettingsResponse)
async def update_org_settings(
    data: OrgSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update organization settings.
    Only admins can update settings.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with an organization",
        )
    
    org = await db.get(Org, current_user.org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    # Update fields
    if data.name is not None:
        org.name = data.name
    
    if data.timezone is not None:
        org.timezone = data.timezone
    
    if data.settings is not None:
        # Merge settings instead of replacing
        current_settings = org.settings or {}
        update_data = data.settings.model_dump(exclude_none=True)
        current_settings.update(update_data)
        org.settings = current_settings
    
    await db.commit()
    await db.refresh(org)
    
    return OrgSettingsResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        timezone=org.timezone,
        is_active=org.is_active,
        settings=org.settings or {},
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


# ============================================================================
# System Information Endpoints
# ============================================================================

@router.get("/system", response_model=SystemInfoResponse)
async def get_system_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get system information and status.
    Available to all authenticated users.
    """
    # Count users in org
    user_count_query = select(func.count(User.id)).where(
        User.org_id == current_user.org_id
    )
    user_result = await db.execute(user_count_query)
    total_users = user_result.scalar() or 0
    
    # Count devices in org
    device_count_query = select(func.count(Device.id)).where(
        Device.org_id == current_user.org_id
    )
    device_result = await db.execute(device_count_query)
    total_devices = device_result.scalar() or 0
    
    # Check face service status
    face_service_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.FACE_SERVICE_URL}/health")
            if response.status_code == 200:
                face_service_status = "online"
            else:
                face_service_status = "offline"
    except Exception:
        face_service_status = "offline"
    
    # Calculate uptime
    uptime_seconds = (datetime.utcnow() - _server_start_time).total_seconds()
    uptime_hours = round(uptime_seconds / 3600, 2)
    
    return SystemInfoResponse(
        version="1.0.0",
        environment="development" if settings.DEBUG else "production",
        face_service_status=face_service_status,
        database_status="connected",  # If we got here, DB is connected
        total_users=total_users,
        total_devices=total_devices,
        uptime_hours=uptime_hours,
    )


@router.get("/test-face-service", response_model=FaceServiceTestResponse)
async def test_face_service(
    current_user: User = Depends(require_admin),
):
    """
    Test face service connection and measure latency.
    Only admins can test the face service.
    """
    start_time = datetime.utcnow()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.FACE_SERVICE_URL}/health")
            
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                return FaceServiceTestResponse(
                    status="online",
                    latency_ms=round(latency_ms, 2),
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Face service returned status {response.status_code}",
                )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Face service request timed out",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot connect to face service",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Face service error: {str(e)}",
        )
