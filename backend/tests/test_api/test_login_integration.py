"""Real database-backed login and token-purpose regression."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.auth.jwt import decode_token, get_password_hash
from src.models.user import User, UserRole


@pytest.mark.asyncio
async def test_real_login_argon2_utc_timestamp_and_refresh_purpose(client, db_session):
    email = f"login-{uuid4().hex[:10]}@example.test"
    password = "CI-example-password-ABC-1234567"
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    login = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert login.status_code == 200, login.text
    payload = login.json()
    assert user.last_login is not None
    assert isinstance(user.last_login, datetime)
    assert user.last_login.tzinfo is None
    assert decode_token(payload["access_token"]) is not None
    assert decode_token(payload["refresh_token"]) is None

    access = {"Authorization": f"Bearer {payload['access_token']}"}
    whoami = await client.get("/api/v1/auth/me", headers=access)
    assert whoami.status_code == 200
    assert whoami.json()["email"] == email
    refresh_bearer = {"Authorization": f"Bearer {payload['refresh_token']}"}
    forbidden = await client.get("/api/v1/auth/me", headers=refresh_bearer)
    assert forbidden.status_code == 401

    renewed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": payload["refresh_token"]},
    )
    assert renewed.status_code == 200, renewed.text
    assert decode_token(renewed.json()["access_token"]) is not None
