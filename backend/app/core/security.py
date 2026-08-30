import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    additional_claims: Mapping[str, object] | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    claims: dict[str, object] = {"sub": str(subject), "exp": expire, "type": "access"}
    if additional_claims:
        claims.update(additional_claims)
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return jwt.encode(
        {"sub": str(subject), "exp": expire, "type": "refresh"},
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None


def verify_access_token(token: str) -> dict[str, Any] | None:
    payload = decode_token(token)
    return payload if payload and payload.get("type") in {"access", "user"} else None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    payload = decode_token(token)
    return payload if payload and payload.get("type") == "refresh" else None


def generate_device_secret() -> str:
    return secrets.token_urlsafe(32)


def create_device_token(
    device_id: str,
    organization_id: str,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.DEVICE_TOKEN_EXPIRE_DAYS)
    )
    return jwt.encode(
        {
            "sub": device_id,
            "org_id": organization_id,
            "ver": token_version,
            "exp": expire,
            "type": "device",
        },
        settings.DEVICE_TOKEN_SECRET,
        algorithm="HS256",
    )


def verify_device_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.DEVICE_TOKEN_SECRET, algorithms=["HS256"])
    except JWTError:
        return None
    return payload if payload.get("type") == "device" else None
