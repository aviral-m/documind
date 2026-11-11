from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select, update

from app.auth.passwords import PasswordPolicyError
from app.auth.tokens import decode_access_token
from app.models import AuthToken, RefreshToken, User
from app.services import auth_service
from app.services.auth_service import InvalidCredentials, InvalidToken

PASSWORD = "correct-horse-battery"
EMAIL = "alice@example.com"


def register_and_verify(db, settings, sender, email=EMAIL, password=PASSWORD):
    auth_service.register(db, settings, sender, email, password)
    auth_service.verify_email(db, sender.sent[-1].token)


def test_register_creates_unverified_user_and_sends_one_email(db, settings, sender):
    auth_service.register(db, settings, sender, "Alice@Example.com", PASSWORD)

    user = db.scalar(select(User).where(User.email == EMAIL))
    assert user is not None
    assert user.is_verified is False
    assert user.hashed_password != PASSWORD
    assert len(sender.sent) == 1
    assert sender.sent[0].to == EMAIL
    assert sender.sent[0].body.count("http://app.test/verify-email?token=") == 1


def test_register_existing_email_is_silent_and_creates_no_duplicate(db, settings, sender):
    auth_service.register(db, settings, sender, EMAIL, PASSWORD)
    auth_service.register(db, settings, sender, EMAIL, "another-password-1")

    users = db.scalars(select(User)).all()
    assert len(users) == 1
    assert len(sender.sent) == 1


def test_register_rejects_password_equal_to_email(db, settings, sender):
    with pytest.raises(PasswordPolicyError):
        auth_service.register(db, settings, sender, EMAIL, EMAIL)


def test_verify_email_marks_user_verified_and_link_is_single_use(db, settings, sender):
    auth_service.register(db, settings, sender, EMAIL, PASSWORD)
    token = sender.sent[0].token

    auth_service.verify_email(db, token)

    assert db.scalar(select(User).where(User.email == EMAIL)).is_verified is True
    with pytest.raises(InvalidToken):
        auth_service.verify_email(db, token)


def test_expired_verification_link_is_rejected(db, settings, sender):
    auth_service.register(db, settings, sender, EMAIL, PASSWORD)
    db.execute(update(AuthToken).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()

    with pytest.raises(InvalidToken):
        auth_service.verify_email(db, sender.sent[0].token)


def test_resending_verification_invalidates_the_older_link(db, settings, sender):
    auth_service.register(db, settings, sender, EMAIL, PASSWORD)
    old_token = sender.sent[0].token

    auth_service.resend_verification(db, settings, sender, EMAIL)

    with pytest.raises(InvalidToken):
        auth_service.verify_email(db, old_token)
    auth_service.verify_email(db, sender.sent[1].token)


def test_resend_verification_for_unknown_email_sends_nothing(db, settings, sender):
    auth_service.resend_verification(db, settings, sender, "nobody@example.com")

    assert sender.sent == []


def test_login_with_wrong_password_or_unknown_email_fails_the_same_way(db, settings, sender):
    register_and_verify(db, settings, sender)

    with pytest.raises(InvalidCredentials):
        auth_service.login(db, settings, EMAIL, "wrong-password-1", None, None)
    with pytest.raises(InvalidCredentials):
        auth_service.login(db, settings, "nobody@example.com", PASSWORD, None, None)


def test_unverified_user_can_log_in_and_token_identifies_them(db, settings, sender):
    auth_service.register(db, settings, sender, EMAIL, PASSWORD)

    pair = auth_service.login(db, settings, EMAIL, PASSWORD, "pytest", "127.0.0.1")

    user = db.scalar(select(User).where(User.email == EMAIL))
    assert decode_access_token(pair.access_token, settings.auth_secret) == user.id
    assert pair.expires_in == settings.access_token_ttl_minutes * 60


def test_refresh_rotates_the_token(db, settings, sender):
    register_and_verify(db, settings, sender)
    first = auth_service.login(db, settings, EMAIL, PASSWORD, None, None)

    second = auth_service.refresh(db, settings, first.refresh_token, None, None)

    assert second.refresh_token != first.refresh_token
    assert second.access_token
    rotated = db.scalar(
        select(RefreshToken).where(RefreshToken.replaced_by_id.is_not(None))
    )
    assert rotated is not None


def test_reusing_a_rotated_refresh_token_revokes_the_whole_session(db, settings, sender):
    register_and_verify(db, settings, sender)
    first = auth_service.login(db, settings, EMAIL, PASSWORD, None, None)
    second = auth_service.refresh(db, settings, first.refresh_token, None, None)

    with pytest.raises(InvalidToken):
        auth_service.refresh(db, settings, first.refresh_token, None, None)

    # The legitimate holder of the newer token is signed out too.
    with pytest.raises(InvalidToken):
        auth_service.refresh(db, settings, second.refresh_token, None, None)


def test_logout_revokes_the_session(db, settings, sender):
    register_and_verify(db, settings, sender)
    pair = auth_service.login(db, settings, EMAIL, PASSWORD, None, None)

    auth_service.logout(db, pair.refresh_token)

    with pytest.raises(InvalidToken):
        auth_service.refresh(db, settings, pair.refresh_token, None, None)


def test_logout_leaves_other_devices_signed_in(db, settings, sender):
    register_and_verify(db, settings, sender)
    laptop = auth_service.login(db, settings, EMAIL, PASSWORD, "laptop", None)
    phone = auth_service.login(db, settings, EMAIL, PASSWORD, "phone", None)

    auth_service.logout(db, phone.refresh_token)

    refreshed = auth_service.refresh(db, settings, laptop.refresh_token, None, None)
    assert refreshed.access_token


def test_expired_refresh_token_is_rejected(db, settings, sender):
    register_and_verify(db, settings, sender)
    pair = auth_service.login(db, settings, EMAIL, PASSWORD, None, None)
    db.execute(update(RefreshToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.commit()

    with pytest.raises(InvalidToken):
        auth_service.refresh(db, settings, pair.refresh_token, None, None)


def test_password_reset_changes_password_once_and_signs_out_sessions(db, settings, sender):
    register_and_verify(db, settings, sender)
    old_session = auth_service.login(db, settings, EMAIL, PASSWORD, None, None)
    auth_service.request_password_reset(db, settings, sender, EMAIL)
    token = sender.sent[-1].token

    auth_service.reset_password(db, token, "new-password-456")

    with pytest.raises(InvalidCredentials):
        auth_service.login(db, settings, EMAIL, PASSWORD, None, None)
    assert auth_service.login(db, settings, EMAIL, "new-password-456", None, None)
    with pytest.raises(InvalidToken):
        auth_service.refresh(db, settings, old_session.refresh_token, None, None)
    with pytest.raises(InvalidToken):
        auth_service.reset_password(db, token, "another-password-789")


def test_weak_new_password_does_not_consume_the_reset_link(db, settings, sender):
    register_and_verify(db, settings, sender)
    auth_service.request_password_reset(db, settings, sender, EMAIL)
    token = sender.sent[-1].token

    with pytest.raises(PasswordPolicyError):
        auth_service.reset_password(db, token, "short")

    auth_service.reset_password(db, token, "a-valid-new-password")


def test_forgot_password_for_unknown_email_sends_nothing(db, settings, sender):
    auth_service.request_password_reset(db, settings, sender, "nobody@example.com")

    assert sender.sent == []


def test_access_token_is_a_standard_jwt(db, settings, sender):
    register_and_verify(db, settings, sender)
    pair = auth_service.login(db, settings, EMAIL, PASSWORD, None, None)

    claims = jwt.decode(pair.access_token, settings.auth_secret, algorithms=["HS256"])

    assert claims["type"] == "access"
    assert "exp" in claims
