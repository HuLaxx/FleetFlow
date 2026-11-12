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
    "TokenData",
    "TokenResponse",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "get_password_hash",
    "require_admin",
    "require_dispatcher",
    "require_driver",
    "require_role",
    "require_user",
    "validate_password_strength",
    "verify_password",
]
