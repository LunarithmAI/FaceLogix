"""
Authentication endpoints for FaceLogix.

Provides user and device authentication, token refresh, and logout functionality.
"""

import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_device_token,
    hash_password,
    verify_password,
)
from app.models.device import Device
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    DeviceLoginRequest,
    DeviceLoginResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    UserProfileResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user with email and password.
    
    Returns JWT access token and refresh token for subsequent API calls.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(
            User.email == request.email,
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Create access token
    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={
            "org_id": str(user.org_id),
            "role": user.role,
            "type": "user",
        },
    )
    
    # Create refresh token (random secure token stored in DB)
    import secrets
    refresh_token_raw = secrets.token_urlsafe(64)
    refresh_token_hash = hashlib.sha256(refresh_token_raw.encode()).hexdigest()
    
    # Store refresh token in database
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(db_refresh_token)
    await db.commit()
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_raw,
        token_type="bearer",
        user_id=user.id,
        org_id=user.org_id,
        role=user.role,
        name=user.name,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using a valid refresh token.
    
    The refresh token must be valid and not expired or revoked.
    """
    # Hash the provided refresh token
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    
    # Find the refresh token in database
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at == None,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    db_token = result.scalar_one_or_none()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    # Get user
    user = await db.get(User, db_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Create new access token
    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={
            "org_id": str(user.org_id),
            "role": user.role,
            "type": "user",
        },
    )
    
    return RefreshResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a refresh token (logout).
    
    The refresh token will no longer be valid for obtaining new access tokens.
    """
    # Hash the provided refresh token
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    
    # Find and revoke the refresh token
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()
    
    if db_token:
        db_token.revoked_at = datetime.utcnow()
        await db.commit()
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get the current authenticated user's profile.
    
    Returns user information based on the JWT token.
    """
    return UserProfileResponse(
        id=current_user.id,
        org_id=current_user.org_id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        department=current_user.department,
        is_active=current_user.is_active,
        enrolled_at=current_user.enrolled_at,
        created_at=current_user.created_at,
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the current user's password.
    
    Requires the current password for verification.
    """
    # Verify current password
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a password set",
        )
    
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Update password
    current_user.password_hash = hash_password(request.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/devices/login", response_model=DeviceLoginResponse)
async def device_login(
    request: DeviceLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a device with device ID and secret.
    
    Returns a long-lived device token for kiosk/terminal authentication.
    """
    # Find device
    device = await db.get(Device, request.device_id)
    
    if not device or not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials",
        )
    
    # Verify device secret
    if not verify_password(request.device_secret, device.secret_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials",
        )
    
    # Update last seen timestamp
    device.last_seen_at = datetime.utcnow()
    await db.commit()
    
    # Create device token
    device_token = create_device_token(
        device_id=str(device.id),
        organization_id=str(device.org_id),
        expires_delta=timedelta(days=settings.DEVICE_TOKEN_EXPIRE_DAYS),
    )
    
    return DeviceLoginResponse(
        device_token=device_token,
        token_type="bearer",
        org_id=device.org_id,
        device_name=device.name,
    )
