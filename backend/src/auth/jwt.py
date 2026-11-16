"""
Authentication utilities: JWT tokens and password hashing.
"""

import os
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv
from jose import JWTError, jwt
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel

# Configuration
load_dotenv()  # Local .env support; existing real environment variables win.


def validate_jwt_secret(key: str | None) -> str:
    """Reject missing, short and template authentication secrets in every environment."""
    if not key or len(key) < 32 or key.startswith(("CHANGE_ME", "your-secret-key")):
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a generated secret of at least 32 characters"
        )
    return key


SECRET_KEY = validate_jwt_secret(os.getenv("JWT_SECRET_KEY"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Argon2id for newly issued hashes. Legacy $2a/$2b bcrypt records continue to
# verify through the maintained bcrypt library, avoiding Passlib compatibility
# failures with modern bcrypt releases.
password_hasher = PasswordHasher()


class TokenData(BaseModel):
    """Token payload data."""

    email: str | None = None
    role: str | None = None
    exp: datetime | None = None


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify Argon2id or legacy bcrypt hashes; reject unknown hash formats."""
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    if hashed_password.startswith("$argon2id$"):
        try:
            return password_hasher.verify(hashed_password, plain_password)
        except (VerificationError, InvalidHashError, ValueError):
            return False
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False
    return False


def get_password_hash(password: str) -> str:
    """Issue Argon2id hashes; do not truncate passwords silently."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must not be empty")
    return password_hasher.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str, *, expected_type: str = "access") -> TokenData | None:
    """Decode a valid, unexpired JWT of the requested token type."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        email: str = payload.get("sub")
        role: str = payload.get("role")
        exp = payload.get("exp")

        if email is None:
            return None

        return TokenData(
            email=email, role=role, exp=datetime.fromtimestamp(exp, UTC) if exp else None
        )
    except JWTError:
        return None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets security requirements."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, "Password is strong"
