from datetime import datetime, timedelta, timezone
from typing import Any, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration constants
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain text password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a JWT access token encoding the subject (user ID or email)."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a long-lived JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token, returning its payload dict or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError:
        return None