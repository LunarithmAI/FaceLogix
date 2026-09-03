from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.identity import AuthenticatedIdentity, UserRole
from app.core.time import local_day_bounds
from app.models.device import Device
from app.models.org import Org
from app.models.organizational_unit import ManagerUnitScope, OrganizationalUnit
from app.models.unit_assignment import UserUnitAssignment
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


async def require_device(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    db: DbSession,
) -> Device:
    if identity.kind != "device":
        raise HTTPException(status_code=403, detail="Device authentication required")
    device = await db.get(Device, identity.subject_id)
    if device is None or not device.is_active or device.org_id != identity.org_id:
        raise unauthorized("Device credential is inactive or stale")
    return device


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


async def managed_unit_ids(db: AsyncSession, actor: User) -> set[UUID]:
    if actor.role in ADMIN_ROLES:
        return set(
            (
                await db.scalars(
                    select(OrganizationalUnit.id).where(
                        OrganizationalUnit.org_id == actor.org_id
                    )
                )
            ).all()
        )
    if actor.role != UserRole.MANAGER.value:
        return set()
    return set(
        (
            await db.scalars(
                select(ManagerUnitScope.unit_id)
                .join(
                    OrganizationalUnit,
                    OrganizationalUnit.id == ManagerUnitScope.unit_id,
                )
                .where(
                    ManagerUnitScope.manager_id == actor.id,
                    OrganizationalUnit.org_id == actor.org_id,
                )
            )
        ).all()
    )


async def ensure_user_in_scope(
    db: AsyncSession,
    actor: User,
    target: User,
    on_date: date | None = None,
) -> None:
    if actor.org_id != target.org_id:
        raise HTTPException(status_code=404, detail="User not found")
    if actor.role in ADMIN_ROLES:
        return
    if actor.role != UserRole.MANAGER.value:
        raise HTTPException(status_code=403, detail="Operational access required")
    effective_date = on_date
    if effective_date is None:
        timezone_name = await db.scalar(select(Org.timezone).where(Org.id == actor.org_id))
        if timezone_name is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        effective_date = local_day_bounds(timezone_name)[0]
    unit_id = await db.scalar(
        select(UserUnitAssignment.unit_id).where(
            UserUnitAssignment.org_id == actor.org_id,
            UserUnitAssignment.user_id == target.id,
            UserUnitAssignment.effective_from <= effective_date,
            (
                UserUnitAssignment.effective_to.is_(None)
                | (UserUnitAssignment.effective_to >= effective_date)
            ),
        )
    )
    if unit_id is None or unit_id not in await managed_unit_ids(db, actor):
        raise HTTPException(status_code=403, detail="User is outside managed unit scope")


async def clear_manager_scopes(db: AsyncSession, user: User) -> None:
    await db.execute(delete(ManagerUnitScope).where(ManagerUnitScope.manager_id == user.id))
