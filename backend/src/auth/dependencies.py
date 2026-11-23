"""
Authentication dependencies for protected routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import decode_token
from src.database import get_db
from src.models.user import User, UserRole

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User | None:
    """Get current user from JWT token. Returns None if no valid token."""
    if token is None:
        return None

    token_data = decode_token(token)
    if token_data is None:
        return None

    result = await db.execute(select(User).where(User.email == token_data.email))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    return user


async def require_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Require a valid authenticated user. Raises 401 if not authenticated."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == token_data.email))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    return user


def require_role(allowed_roles: list[UserRole]):
    """Require user to have one of the specified roles."""

    async def role_checker(current_user: User = Depends(require_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


# Convenience dependencies
require_admin = require_role([UserRole.ADMIN])
require_dispatcher = require_role([UserRole.ADMIN, UserRole.DISPATCHER])
require_driver = require_role([UserRole.ADMIN, UserRole.DISPATCHER, UserRole.DRIVER])
