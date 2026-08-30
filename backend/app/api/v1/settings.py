from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_operator
from app.api.tenant import load_org
from app.core.config import settings
from app.core.database import get_db
from app.core.time import utc_now
from app.models.device import Device
from app.models.org import Org
from app.models.user import User
from app.schemas.settings import (
    FaceServiceTestResponse,
    OrgSettingsResponse,
    OrgSettingsUpdate,
    SystemInfoResponse,
    canonical_org_settings,
)
from app.services.face_client import FaceServiceClient, get_face_client

router = APIRouter(prefix="/settings", tags=["settings"])
_server_start_time = utc_now()


def org_response(org: Org) -> OrgSettingsResponse:
    return OrgSettingsResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        timezone=org.timezone,
        is_active=org.is_active,
        settings=canonical_org_settings(org.settings),
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.get("/org", response_model=OrgSettingsResponse)
async def get_org_settings(
    current_user: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgSettingsResponse:
    return org_response(await load_org(db, current_user.org_id))


@router.patch("/org", response_model=OrgSettingsResponse)
async def update_org_settings(
    data: OrgSettingsUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgSettingsResponse:
    org = await load_org(db, current_user.org_id)
    if data.name is not None:
        org.name = data.name
    if data.timezone is not None:
        org.timezone = data.timezone
    if data.settings is not None:
        stored_settings = dict(org.settings or {})
        stored_settings.update(data.settings.model_dump(exclude_none=True))
        org.settings = stored_settings
    await db.commit()
    await db.refresh(org)
    return org_response(org)


@router.get("/system", response_model=SystemInfoResponse)
async def get_system_info(
    current_user: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> SystemInfoResponse:
    user_count = await db.scalar(
        select(func.count(User.id)).where(User.org_id == current_user.org_id)
    )
    device_count = await db.scalar(
        select(func.count(Device.id)).where(Device.org_id == current_user.org_id)
    )
    uptime_hours = (utc_now() - _server_start_time).total_seconds() / 3600
    return SystemInfoResponse(
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        face_service_status="online" if await face_client.ready() else "offline",
        database_status="connected",
        total_users=user_count or 0,
        total_devices=device_count or 0,
        uptime_hours=round(uptime_hours, 2),
    )


@router.get("/test-face-service", response_model=FaceServiceTestResponse)
async def test_face_service(
    _current_user: Annotated[User, Depends(require_admin)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> FaceServiceTestResponse:
    started = monotonic()
    if not await face_client.ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_UNAVAILABLE",
                "message": "Face analysis service is unavailable",
            },
        )
    return FaceServiceTestResponse(
        status="online",
        latency_ms=round((monotonic() - started) * 1000, 2),
    )
