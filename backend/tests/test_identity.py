from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.api.deps import (
    ensure_role_assignment_allowed,
    ensure_target_user_mutable,
    get_current_identity,
)
from app.api.v1.devices import (
    deactivate_device,
    delete_device,
    regenerate_device_secret,
    update_device,
)
from app.core.config import Settings
from app.core.security import create_access_token, create_device_token
from app.models.device import Device
from app.models.user import User
from app.schemas.device import DeviceUpdate
from app.schemas.user import UserUpdate


class FakeSession:
    def __init__(self, entity: object) -> None:
        self.entity = entity
        self.commits = 0

    async def get(self, model: type[object], entity_id: object) -> object | None:
        return self.entity if getattr(self.entity, "id", None) == entity_id else None

    async def scalar(self, _statement: object) -> object:
        return self.entity

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, entity: object) -> None:
        return None


def make_device() -> Device:
    device = Device(
        id=uuid4(),
        org_id=uuid4(),
        name="Kiosk",
        device_type="kiosk",
        secret_hash="unused",
        token_version=1,
        is_active=True,
        settings={},
    )
    device.created_at = datetime.now(UTC)
    device.updated_at = device.created_at
    return device


def make_actor(org_id: object, role: str = "manager") -> User:
    now = datetime.now(UTC)
    actor = User(id=uuid4(), org_id=org_id, name="Operator", role=role, is_active=True)
    actor.created_at = now
    actor.updated_at = now
    return actor


def test_user_patch_rejects_password_field() -> None:
    with pytest.raises(ValidationError):
        UserUpdate.model_validate({"password": "plaintext-password"})


def test_required_secrets_have_no_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("DEVICE_TOKEN_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["patch", "delete", "deactivate", "regenerate"])
async def test_each_device_invalidation_path_increments_once(operation: str) -> None:
    device = make_device()
    session = FakeSession(device)
    actor = make_actor(device.org_id)

    if operation == "patch":
        await update_device(device.id, DeviceUpdate(is_active=False), session, actor)  # type: ignore[arg-type]
    elif operation == "delete":
        await delete_device(device.id, session, actor)  # type: ignore[arg-type]
    elif operation == "deactivate":
        await deactivate_device(device.id, session, actor)  # type: ignore[arg-type]
    else:
        await regenerate_device_secret(device.id, session, actor)  # type: ignore[arg-type]

    assert device.token_version == 2

    if operation in {"patch", "delete", "deactivate"}:
        if operation == "patch":
            await update_device(device.id, DeviceUpdate(is_active=False), session, actor)  # type: ignore[arg-type]
        elif operation == "delete":
            await delete_device(device.id, session, actor)  # type: ignore[arg-type]
        else:
            await deactivate_device(device.id, session, actor)  # type: ignore[arg-type]
        assert device.token_version == 2


@pytest.mark.asyncio
async def test_device_token_requires_current_version_and_database_tenant() -> None:
    device = make_device()
    token = create_device_token(str(device.id), str(device.org_id), device.token_version)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = FakeSession(device)

    identity = await get_current_identity(credentials, session)  # type: ignore[arg-type]
    assert identity.subject_id == device.id
    assert identity.org_id == device.org_id

    device.token_version += 1
    with pytest.raises(HTTPException) as exc_info:
        await get_current_identity(credentials, session)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_user_identity_uses_current_database_role_and_active_state() -> None:
    user = make_actor(uuid4(), "member")
    token = create_access_token(str(user.id), additional_claims={"role": "super_admin"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = FakeSession(user)

    identity = await get_current_identity(credentials, session)  # type: ignore[arg-type]
    assert identity.role is not None
    assert identity.role.value == "member"

    user.is_active = False
    with pytest.raises(HTTPException) as exc_info:
        await get_current_identity(credentials, session)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 401


@pytest.mark.parametrize("role", ["manager", "admin", "super_admin"])
def test_manager_cannot_assign_elevated_roles(role: str) -> None:
    actor = make_actor(uuid4(), "manager")
    with pytest.raises(HTTPException) as exc_info:
        ensure_role_assignment_allowed(actor, role)
    assert exc_info.value.status_code == 403


def test_manager_cannot_mutate_elevated_target() -> None:
    org_id = uuid4()
    actor = make_actor(org_id, "manager")
    target = make_actor(org_id, "admin")
    with pytest.raises(HTTPException) as exc_info:
        ensure_target_user_mutable(actor, target)
    assert exc_info.value.status_code == 403
