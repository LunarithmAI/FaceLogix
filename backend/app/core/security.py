from datetime import datetime, timedelta
from typing import Optional, Union
import secrets

from jose import jwt, JWTError
import bcrypt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[dict]:
    """Verify an access token and return the payload."""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def verify_refresh_token(token: str) -> Optional[dict]:
    """Verify a refresh token and return the payload."""
    payload = decode_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None


def generate_device_secret() -> str:
    """Generate a secure random device secret."""
    return secrets.token_urlsafe(32)


def create_device_token(
    device_id: str,
    organization_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT token for device authentication."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.DEVICE_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": device_id,
        "org": organization_id,
        "exp": expire,
        "type": "device"
    }
    
    return jwt.encode(to_encode, settings.DEVICE_TOKEN_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_device_token(token: str) -> Optional[dict]:
    """Verify a device token and return the payload."""
    try:
        payload = jwt.decode(
            token,
            settings.DEVICE_TOKEN_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") == "device":
            return payload
        return None
    except JWTError:
        return None
