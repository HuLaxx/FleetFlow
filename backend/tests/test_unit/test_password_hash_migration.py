"""Password hashing and legacy verification migration acceptance."""

import bcrypt
import pytest

from src.auth.jwt import get_password_hash, verify_password


def test_new_password_hash_is_argon2id_and_verifies():
    password = "A-long-synthetic-CI-password-12345"
    digest = get_password_hash(password)
    assert digest.startswith("$argon2id$")
    assert verify_password(password, digest)
    assert not verify_password("wrong", digest)
    assert not verify_password(password, "garbage")


def test_legacy_bcrypt_hashes_remain_verifiable_without_passlib():
    password = "legacy-secret-ABC123"
    legacy = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    assert verify_password(password, legacy)
    assert not verify_password("other-legacy-secret", legacy)


def test_rejects_empty_and_unknown_hash_types():
    assert not verify_password("secret", "not-a-password-hash")
    assert not verify_password("", "not-a-password-hash")
    assert not verify_password("secret", "$argon2id$invalid")
    with pytest.raises(ValueError, match="empty"):
        get_password_hash("")
