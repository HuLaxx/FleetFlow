"""
Authentication package.
"""

from src.auth.dependencies import (
    get_current_user,
    require_admin,
    require_dispatcher,
    require_driver,
    require_role,
    require_user,
)
from src.auth.jwt import (
    TokenData,
    TokenResponse,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)

__all__ = [
    # JWT utilities
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "validate_password_strength",
    "TokenData",
    "TokenResponse",
    # Dependencies
    "get_current_user",
    "require_user",
    "require_role",
    "require_admin",
    "require_dispatcher",
    "require_driver",
]
