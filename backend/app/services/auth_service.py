from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import (
    create_access_token,
    create_device_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.models import Device, RefreshToken, User


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[User, str, str]:
        """
        Authenticate a user with email and password.
        
        Returns:
            Tuple of (user, access_token, refresh_token)
        
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Find user by email
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.is_active == True
            )
        )
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise AuthenticationError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS"
            )

        if not verify_password(password, user.password_hash):
            raise AuthenticationError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS"
            )

        # Create tokens
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "org": str(user.org_id),
                "role": user.role,
                "name": user.name
            }
        )
        
        refresh_token = create_refresh_token(subject=str(user.id))

        # Store refresh token hash
        token_hash = hash_password(refresh_token)
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.db.add(db_refresh_token)
        await self.db.commit()

        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, int]:
        """
        Refresh an access token using a refresh token.
        
        Returns:
            Tuple of (new_access_token, expires_in_seconds)
        
        Raises:
            AuthenticationError: If refresh token is invalid or expired
        """
        # Verify the refresh token
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise AuthenticationError(
                message="Invalid refresh token",
                code="INVALID_REFRESH_TOKEN"
            )

        user_id = UUID(payload["sub"])

        # Find the user
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError(
                message="User not found or inactive",
                code="USER_NOT_FOUND"
            )

        # Find and validate stored refresh token
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at == None,
                RefreshToken.expires_at > datetime.utcnow()
            )
        )
        stored_tokens = result.scalars().all()

        # Check if any stored token matches
        valid_token = None
        for token in stored_tokens:
            if verify_password(refresh_token, token.token_hash):
                valid_token = token
                break

        if not valid_token:
            raise AuthenticationError(
                message="Refresh token not found or revoked",
                code="REFRESH_TOKEN_REVOKED"
            )

        # Create new access token
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "org": str(user.org_id),
                "role": user.role,
                "name": user.name
            }
        )

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return access_token, expires_in

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """
        Revoke a refresh token.
        
        Returns:
            True if token was revoked, False if not found
        """
        payload = verify_refresh_token(refresh_token)
        if not payload:
            return False

        user_id = UUID(payload["sub"])

        # Find stored refresh tokens for this user
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at == None
            )
        )
        stored_tokens = result.scalars().all()

        # Find and revoke matching token
        for token in stored_tokens:
            if verify_password(refresh_token, token.token_hash):
                token.revoked_at = datetime.utcnow()
                await self.db.commit()
                return True

        return False

    async def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Returns:
            Number of tokens revoked
        """
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at == None
            )
        )
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            token.revoked_at = datetime.utcnow()
            count += 1

        if count > 0:
            await self.db.commit()

        return count

    async def authenticate_device(
        self, device_id: UUID, device_secret: str
    ) -> Tuple[Device, str]:
        """
        Authenticate a device with ID and secret.
        
        Returns:
            Tuple of (device, access_token)
        
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Find device
        result = await self.db.execute(
            select(Device).where(
                Device.id == device_id,
                Device.is_active == True
            )
        )
        device = result.scalar_one_or_none()

        if not device:
            raise AuthenticationError(
                message="Invalid device credentials",
                code="INVALID_DEVICE_CREDENTIALS"
            )

        if not verify_password(device_secret, device.secret_hash):
            raise AuthenticationError(
                message="Invalid device credentials",
                code="INVALID_DEVICE_CREDENTIALS"
            )

        # Update last seen
        device.last_seen_at = datetime.utcnow()
        await self.db.commit()

        # Create device token
        access_token = create_device_token(
            device_id=str(device.id),
            organization_id=str(device.org_id)
        )

        return device, access_token

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_device_by_id(self, device_id: UUID) -> Optional[Device]:
        """Get a device by ID."""
        result = await self.db.execute(
            select(Device).where(Device.id == device_id)
        )
        return result.scalar_one_or_none()
