"""
Authentication package.
"""

from src.auth.jwt import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_password_strength,
    TokenData,
    TokenResponse,
)

from src.auth.dependencies import (
    get_current_user,
    require_user,
    require_role,
    require_admin,
    require_dispatcher,
    require_driver,
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
