from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import generate_device_secret, hash_password
from app.models import Device
from app.schemas.device import DeviceCreate, DeviceUpdate


class DeviceService:
    """Service for handling device operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_devices(
        self,
        org_id: UUID,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        device_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Device], int]:
        """
        List devices for an organization with pagination and filters.
        
        Returns:
            Tuple of (devices, total_count)
        """
        query = select(Device).where(Device.org_id == org_id)

        # Apply filters
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Device.name.ilike(search_pattern)) |
                (Device.location.ilike(search_pattern))
            )

        if device_type:
            query = query.where(Device.device_type == device_type)

        if is_active is not None:
            query = query.where(Device.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Device.name).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        devices = list(result.scalars().all())

        return devices, total

    async def create_device(
        self, org_id: UUID, data: DeviceCreate
    ) -> Tuple[Device, str]:
        """
        Create a new device.
        
        Returns:
            Tuple of (device, device_secret)
        """
        # Generate device secret
        device_secret = generate_device_secret()
        secret_hash = hash_password(device_secret)

        device = Device(
            org_id=org_id,
            name=data.name,
            location=data.location,
            device_type=data.device_type,
            secret_hash=secret_hash,
            settings=data.settings or {},
            is_active=True
        )

        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)

        return device, device_secret

    async def get_device(self, org_id: UUID, device_id: UUID) -> Device:
        """
        Get a device by ID.
        
        Raises:
            NotFoundError: If device not found
        """
        result = await self.db.execute(
            select(Device).where(
                Device.id == device_id,
                Device.org_id == org_id
            )
        )
        device = result.scalar_one_or_none()

        if not device:
            raise NotFoundError(
                message="Device not found",
                resource_type="Device",
                resource_id=str(device_id)
            )

        return device

    async def update_device(
        self, org_id: UUID, device_id: UUID, data: DeviceUpdate
    ) -> Device:
        """
        Update a device.
        
        Raises:
            NotFoundError: If device not found
        """
        device = await self.get_device(org_id, device_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(device, field, value)

        await self.db.commit()
        await self.db.refresh(device)

        return device

    async def delete_device(self, org_id: UUID, device_id: UUID) -> bool:
        """
        Delete a device.
        
        Raises:
            NotFoundError: If device not found
        """
        device = await self.get_device(org_id, device_id)

        await self.db.delete(device)
        await self.db.commit()

        return True

    async def regenerate_secret(
        self, org_id: UUID, device_id: UUID
    ) -> Tuple[Device, str]:
        """
        Regenerate the secret for a device.
        
        Returns:
            Tuple of (device, new_device_secret)
        
        Raises:
            NotFoundError: If device not found
        """
        device = await self.get_device(org_id, device_id)

        # Generate new secret
        device_secret = generate_device_secret()
        device.secret_hash = hash_password(device_secret)

        await self.db.commit()
        await self.db.refresh(device)

        return device, device_secret

    async def update_last_seen(self, device_id: UUID) -> None:
        """Update the last_seen_at timestamp for a device."""
        result = await self.db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()

        if device:
            device.last_seen_at = datetime.utcnow()
            await self.db.commit()

    async def get_active_devices_count(self, org_id: UUID) -> int:
        """Get count of active devices for an organization."""
        result = await self.db.execute(
            select(func.count()).where(
                Device.org_id == org_id,
                Device.is_active == True
            )
        )
        return result.scalar() or 0
