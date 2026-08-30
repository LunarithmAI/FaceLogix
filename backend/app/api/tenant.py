from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.org import Org
from app.models.user import User


async def load_org(db: AsyncSession, org_id: UUID) -> Org:
    org = await db.scalar(select(Org).where(Org.id == org_id))
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def load_user(db: AsyncSession, org_id: UUID, user_id: UUID) -> User:
    user = await db.scalar(select(User).where(User.id == user_id, User.org_id == org_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def load_device(db: AsyncSession, org_id: UUID, device_id: UUID) -> Device:
    device = await db.scalar(select(Device).where(Device.id == device_id, Device.org_id == org_id))
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device
