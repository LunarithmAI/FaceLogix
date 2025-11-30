"""
Device management endpoints for FaceLogix.

Provides CRUD operations for kiosks, tablets, and other check-in devices.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.security import generate_device_secret, hash_password
from app.models.device import Device
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.device import (
    DeviceCreate,
    DeviceCreateResponse,
    DeviceResponse,
    DeviceUpdate,
)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List all devices in the organization with pagination.
    
    Admin only.
    """
    # Base query
    query = select(Device).where(Device.org_id == current_user.org_id)
    count_query = select(func.count(Device.id)).where(Device.org_id == current_user.org_id)
    
    # Apply filters
    if is_active is not None:
        query = query.where(Device.is_active == is_active)
        count_query = count_query.where(Device.is_active == is_active)
    
    if device_type:
        query = query.where(Device.device_type == device_type)
        count_query = count_query.where(Device.device_type == device_type)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Calculate pagination
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Execute query with pagination
    query = query.order_by(Device.name).offset(offset).limit(page_size)
    result = await db.execute(query)
    devices = result.scalars().all()
    
    return PaginatedResponse(
        items=[DeviceResponse.model_validate(device) for device in devices],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=DeviceCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new device.
    
    Returns device_id and device_secret. The secret is only shown once
    and must be saved securely for device authentication.
    
    Admin only.
    """
    # Generate device secret
    device_secret = generate_device_secret()
    secret_hash = hash_password(device_secret)
    
    # Create device
    device = Device(
        org_id=current_user.org_id,
        name=device_data.name,
        location=device_data.location,
        device_type=device_data.device_type,
        secret_hash=secret_hash,
        settings=device_data.settings or {},
    )
    
    db.add(device)
    await db.commit()
    await db.refresh(device)
    
    return DeviceCreateResponse(
        id=device.id,
        name=device.name,
        device_secret=device_secret,  # Only returned on creation!
        org_id=device.org_id,
        created_at=device.created_at,
    )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get a device by ID.
    
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    return DeviceResponse.model_validate(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update device details.
    
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    # Update fields if provided
    update_data = device_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(device, field, value)
    
    await db.commit()
    await db.refresh(device)
    
    return DeviceResponse.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Soft delete a device (sets is_active=False).
    
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    # Soft delete
    device.is_active = False
    await db.commit()


@router.post("/{device_id}/regenerate-secret", response_model=DeviceCreateResponse)
async def regenerate_device_secret(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Regenerate device secret.
    
    This invalidates any existing device tokens and requires re-authentication.
    The new secret is only returned once and must be saved securely.
    
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    # Generate new secret
    new_secret = generate_device_secret()
    device.secret_hash = hash_password(new_secret)
    
    await db.commit()
    await db.refresh(device)
    
    return DeviceCreateResponse(
        id=device.id,
        name=device.name,
        device_secret=new_secret,
        org_id=device.org_id,
        created_at=device.created_at,
    )


@router.post("/{device_id}/activate", response_model=DeviceResponse)
async def activate_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Activate a device.
    
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    device.is_active = True
    await db.commit()
    await db.refresh(device)
    
    return DeviceResponse.model_validate(device)


@router.post("/{device_id}/deactivate", response_model=DeviceResponse)
async def deactivate_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Deactivate a device.
    
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    device.is_active = False
    await db.commit()
    await db.refresh(device)
    
    return DeviceResponse.model_validate(device)


@router.patch("/{device_id}/settings", response_model=DeviceResponse)
async def update_device_settings(
    device_id: UUID,
    settings: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update device settings.
    
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    # Merge settings
    current_settings = device.settings or {}
    current_settings.update(settings)
    device.settings = current_settings
    
    await db.commit()
    await db.refresh(device)
    
    return DeviceResponse.model_validate(device)


@router.post("/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Record device heartbeat/ping.
    
    Updates the last_seen_at timestamp.
    Admin only.
    """
    device = await db.get(Device, device_id)
    
    if not device or device.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    device.last_seen_at = datetime.utcnow()
    await db.commit()
    
    return {
        "status": "active" if device.is_active else "inactive",
        "last_active_at": device.last_seen_at.isoformat(),
    }
