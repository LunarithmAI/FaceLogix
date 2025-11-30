"""
API Dependencies for FaceLogix Backend.

Provides dependency injection for database sessions, authentication,
and authorization across all API endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User

# HTTP Bearer security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncSession:
    """
    Dependency that provides a database session.
    Automatically closes the session when the request completes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Decode JWT and return identity payload.
    Works for both user tokens and device tokens.
    
    Returns a dict with:
        - sub: User ID or Device ID
        - org_id: Organization ID
        - type: "user" or "device"
        - role: User role (for user tokens only)
    """
    token = credentials.credentials
    
    # Try user token first
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        token_type = payload.get("type", "access")
        
        if token_type in ("access", "user"):
            return {
                "sub": payload.get("sub"),
                "org_id": payload.get("org_id"),
                "type": "user",
                "role": payload.get("role"),
            }
    except JWTError:
        pass
    
    # Try device token
    try:
        payload = jwt.decode(
            token,
            settings.DEVICE_TOKEN_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") == "device":
            return {
                "sub": payload.get("sub"),
                "org_id": payload.get("org"),
                "type": "device",
                "role": None,
            }
    except JWTError:
        pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_identity(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[dict]:
    """
    Optional version of get_current_identity.
    Returns None if no valid token is provided.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_identity(credentials)
    except HTTPException:
        return None


async def get_current_user(
    identity: dict = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user from token.
    Raises error if token is for a device or user not found.
    """
    if identity.get("type") != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User authentication required",
        )
    
    user_id = identity.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    try:
        user = await db.get(User, UUID(user_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require admin or super_admin role.
    Returns the current user if authorized.
    """
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require super_admin role.
    Returns the current user if authorized.
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


def require_permission(permission: str):
    """
    Dependency factory for permission checking.
    
    Usage:
        @router.get("/users")
        async def list_users(
            user: User = Depends(require_permission("user:read"))
        ):
            ...
    """
    # Permission to role mapping
    PERMISSION_ROLES = {
        "user:read": ("admin", "super_admin"),
        "user:create": ("admin", "super_admin"),
        "user:update": ("admin", "super_admin"),
        "user:delete": ("admin", "super_admin"),
        "user:enroll": ("admin", "super_admin"),
        "device:read": ("admin", "super_admin"),
        "device:create": ("admin", "super_admin"),
        "device:update": ("admin", "super_admin"),
        "device:delete": ("admin", "super_admin"),
        "attendance:read": ("member", "admin", "super_admin"),
        "attendance:read_all": ("admin", "super_admin"),
        "attendance:create": ("member", "admin", "super_admin"),
        "report:read": ("admin", "super_admin"),
        "report:export": ("admin", "super_admin"),
        "org:read": ("admin", "super_admin"),
        "org:update": ("super_admin",),
    }
    
    async def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        allowed_roles = PERMISSION_ROLES.get(permission, ())
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user
    
    return permission_checker
