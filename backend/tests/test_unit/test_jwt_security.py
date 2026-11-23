"""JWT signing keys must be configured; public fallback keys enable route approval forgery."""

import pytest

from src.auth.jwt import validate_jwt_secret


@pytest.mark.parametrize(
    "weak_key",
    [
        None,
        "",
        "short-secret",
        "your-secret-key-change-in-production-immediately",
        "CHANGE_ME_GENERATE_SECURE_KEY_AT_LEAST_32_CHARS",
    ],
)
def test_missing_or_template_jwt_signing_secrets_fail_closed(weak_key):
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validate_jwt_secret(weak_key)


def test_strong_generated_jwt_secret_is_accepted():
    key = "synthetic-ci-only-test-key-with-at-least-32-characters"
    assert validate_jwt_secret(key) == key
