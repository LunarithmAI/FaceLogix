from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.identity import AuthenticatedIdentity, UserRole
from app.models.device import Device
from app.models.user import User

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


DbSession = Annotated[AsyncSession, Depends(get_db)]


def unauthorized(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _uuid_claim(payload: dict[str, object], name: str) -> UUID:
    value = payload.get(name)
    if not isinstance(value, str):
        raise unauthorized("Invalid token payload")
    try:
        return UUID(value)
    except ValueError as exc:
        raise unauthorized("Invalid token payload") from exc


async def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: DbSession,
) -> AuthenticatedIdentity:
    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") in {"access", "user"}:
            user_id = _uuid_claim(payload, "sub")
            user = await db.get(User, user_id)
            if user is None or not user.is_active:
                raise unauthorized("User account is inactive or missing")
            try:
                role = UserRole(user.role)
            except ValueError as exc:
                raise unauthorized("User role is invalid") from exc
            return AuthenticatedIdentity(
                subject_id=user.id,
                org_id=user.org_id,
                kind="user",
                role=role,
            )
    except JWTError:
        pass

    try:
        payload = jwt.decode(token, settings.DEVICE_TOKEN_SECRET, algorithms=["HS256"])
        if payload.get("type") == "device":
            device_id = _uuid_claim(payload, "sub")
            org_id = _uuid_claim(payload, "org_id")
            version = payload.get("ver")
            device = await db.get(Device, device_id)
            if (
                device is None
                or not device.is_active
                or device.org_id != org_id
                or not isinstance(version, int)
                or device.token_version != version
            ):
                raise unauthorized("Device credential is inactive or stale")
            return AuthenticatedIdentity(
                subject_id=device.id,
                org_id=device.org_id,
                kind="device",
            )
    except JWTError:
        pass

    raise unauthorized()


async def get_optional_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    db: DbSession,
) -> AuthenticatedIdentity | None:
    if credentials is None:
        return None
    try:
        return await get_current_identity(credentials, db)
    except HTTPException:
        return None


async def get_current_user(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    db: DbSession,
) -> User:
    if identity.kind != "user":
        raise HTTPException(status_code=403, detail="User authentication required")
    user = await db.get(User, identity.subject_id)
    if user is None or not user.is_active or user.org_id != identity.org_id:
        raise unauthorized("User account is inactive or missing")
    return user


OPERATOR_ROLES = {UserRole.MANAGER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}
ADMIN_ROLES = {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}


async def require_operator(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role not in OPERATOR_ROLES:
        raise HTTPException(status_code=403, detail="Operational access required")
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_super_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


def ensure_role_assignment_allowed(actor: User, role: str) -> None:
    if actor.role == UserRole.MANAGER.value and role != UserRole.MEMBER.value:
        raise HTTPException(status_code=403, detail="Managers may assign only the member role")


def ensure_target_user_mutable(actor: User, target: User) -> None:
    if actor.org_id != target.org_id:
        raise HTTPException(status_code=404, detail="User not found")
    if actor.role == UserRole.MANAGER.value and target.role != UserRole.MEMBER.value:
        raise HTTPException(status_code=403, detail="Managers may modify only member users")
