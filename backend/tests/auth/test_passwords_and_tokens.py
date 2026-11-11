import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.passwords import (
    PasswordPolicyError,
    hash_password,
    validate_password,
    verify_password,
)
from app.auth.tokens import (
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_opaque_token,
)

SECRET = "test-secret-that-is-long-enough-for-hs256-0123456789"


def test_password_hash_round_trip():
    hashed = hash_password("correct horse")

    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong horse", hashed)


def test_password_policy_rejects_short_passwords():
    with pytest.raises(PasswordPolicyError):
        validate_password("short", "a@example.com")


def test_password_policy_rejects_password_equal_to_email():
    with pytest.raises(PasswordPolicyError):
        validate_password("A@Example.com", "a@example.com")


def test_password_policy_accepts_eight_characters():
    validate_password("12345678", "a@example.com")


def test_access_token_round_trip_returns_user_id():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, SECRET, ttl_minutes=15)

    assert decode_access_token(token, SECRET) == user_id


def test_access_token_signed_with_other_secret_is_rejected():
    token = create_access_token(uuid.uuid4(), "another-secret-of-sufficient-length-0123456", 15)

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, SECRET)


def test_expired_access_token_is_rejected():
    payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(hours=1),
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, SECRET)


def test_access_token_with_wrong_type_is_rejected():
    payload = {
        "sub": str(uuid.uuid4()),
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, SECRET)


def test_opaque_tokens_are_unique_and_hash_deterministically():
    first = generate_opaque_token()
    second = generate_opaque_token()

    assert first != second
    assert hash_opaque_token(first) == hash_opaque_token(first)
    assert hash_opaque_token(first) != first
