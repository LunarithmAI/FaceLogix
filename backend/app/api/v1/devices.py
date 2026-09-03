from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_device
from app.api.tenant import load_device
from app.core.database import get_db
from app.core.security import generate_device_secret, hash_password
from app.core.time import utc_now
from app.models.device import Device
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.device import (
    DeviceCreate,
    DeviceCreateResponse,
    DeviceResponse,
    DeviceSettingsData,
    DeviceSettingsPatch,
    DeviceUpdate,
    canonical_device_settings,
)

router = APIRouter(prefix="/devices", tags=["Devices"])


def deactivate_device_record(device: Device) -> None:
    if device.is_active:
        device.is_active = False
        device.token_version += 1


def device_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        org_id=device.org_id,
        name=device.name,
        location=device.location,
        device_type=device.device_type,
        is_active=device.is_active,
        last_seen_at=device.last_seen_at,
        settings=canonical_device_settings(device.settings),
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


def device_credentials_response(device: Device, secret: str) -> DeviceCreateResponse:
    response = device_response(device)
    return DeviceCreateResponse(**response.model_dump(), device_secret=secret)


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    device_type: Annotated[str | None, Query(description="Filter by device type")] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
) -> PaginatedResponse[DeviceResponse]:
    conditions = [Device.org_id == current_user.org_id]
    if is_active is not None:
        conditions.append(Device.is_active == is_active)
    if device_type is not None:
        conditions.append(Device.device_type == device_type)
    if search is not None:
        pattern = f"%{search}%"
        conditions.append(or_(Device.name.ilike(pattern), Device.location.ilike(pattern)))
    total = await db.scalar(select(func.count(Device.id)).where(*conditions)) or 0
    devices = (
        await db.scalars(
            select(Device)
            .where(*conditions)
            .order_by(Device.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return PaginatedResponse(
        items=[device_response(device) for device in devices],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 1,
    )


@router.post("", response_model=DeviceCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_data: DeviceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> DeviceCreateResponse:
    device_secret = generate_device_secret()
    device = Device(
        org_id=current_user.org_id,
        name=device_data.name,
        location=device_data.location,
        device_type=device_data.device_type,
        secret_hash=hash_password(device_secret),
        settings=device_data.settings.model_dump(),
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device_credentials_response(device, device_secret)


@router.post("/me/heartbeat", response_model=DeviceSettingsData)
async def device_heartbeat(
    device: Annotated[Device, Depends(require_device)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceSettingsData:
    device.last_seen_at = utc_now()
    await db.commit()
    return canonical_device_settings(device.settings)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> DeviceResponse:
    device = await load_device(db, current_user.org_id, device_id)
    return device_response(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_data: DeviceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> DeviceResponse:
    device = await load_device(db, current_user.org_id, device_id)
    update_data = device_data.model_dump(exclude_unset=True)
    if update_data.get("is_active") is False and device.is_active:
        device.token_version += 1
    for field, value in update_data.items():
        setattr(device, field, value)
    await db.commit()
    await db.refresh(device)
    return device_response(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Response:
    device = await load_device(db, current_user.org_id, device_id)
    deactivate_device_record(device)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{device_id}/regenerate-secret", response_model=DeviceCreateResponse)
async def regenerate_device_secret(
    device_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> DeviceCreateResponse:
    device = await load_device(db, current_user.org_id, device_id)
    new_secret = generate_device_secret()
    device.secret_hash = hash_password(new_secret)
    device.token_version += 1
    device.is_active = True
    await db.commit()
    await db.refresh(device)
    return device_credentials_response(device, new_secret)


@router.post("/{device_id}/activate", response_model=DeviceResponse)
async def activate_device(
    device_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> DeviceResponse:
    device = await load_device(db, current_user.org_id, device_id)
    device.is_active = True
    await db.commit()
    await db.refresh(device)
    return device_response(device)


@router.post("/{device_id}/deactivate", response_model=DeviceResponse)
async def deactivate_device(
    device_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> DeviceResponse:
    device = await load_device(db, current_user.org_id, device_id)
    deactivate_device_record(device)
    await db.commit()
    await db.refresh(device)
    return device_response(device)


@router.patch("/{device_id}/settings", response_model=DeviceResponse)
async def update_device_settings(
    device_id: UUID,
    settings_patch: DeviceSettingsPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> DeviceResponse:
    device = await load_device(db, current_user.org_id, device_id)
    merged = {
        **canonical_device_settings(device.settings).model_dump(),
        **settings_patch.model_dump(exclude_none=True),
    }
    device.settings = DeviceSettingsData.model_validate(merged).model_dump()
    await db.commit()
    await db.refresh(device)
    return device_response(device)
