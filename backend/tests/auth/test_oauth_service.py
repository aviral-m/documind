import pytest
from sqlalchemy import select

from app.auth.oauth import ProviderProfile
from app.models import OAuthAccount, User
from app.services import auth_service
from app.services.auth_service import OAuthEmailNotVerified


def google_profile(**overrides) -> ProviderProfile:
    values = {
        "provider": "google",
        "provider_account_id": "google-123",
        "email": "carol@example.com",
        "email_verified": True,
        "name": "Carol",
        "avatar_url": "https://img.example/carol.png",
    }
    values.update(overrides)
    return ProviderProfile(**values)


def test_new_verified_provider_email_creates_verified_account(db, settings):
    pair = auth_service.login_with_provider(db, settings, google_profile(), None, None)

    user = db.scalar(select(User).where(User.email == "carol@example.com"))
    assert user is not None
    assert user.is_verified is True
    assert user.hashed_password is None
    assert user.name == "Carol"
    account = db.scalar(select(OAuthAccount))
    assert account.user_id == user.id
    assert account.provider == "google"
    assert pair.refresh_token


def test_existing_account_with_same_email_is_linked_not_duplicated(db, settings, sender):
    auth_service.register(db, settings, sender, "carol@example.com", "a-password-123")

    auth_service.login_with_provider(db, settings, google_profile(), None, None)

    users = db.scalars(select(User)).all()
    assert len(users) == 1
    assert users[0].is_verified is True
    assert db.scalar(select(OAuthAccount)).user_id == users[0].id


def test_returning_provider_account_signs_into_the_same_user(db, settings):
    auth_service.login_with_provider(db, settings, google_profile(), None, None)
    auth_service.login_with_provider(db, settings, google_profile(), None, None)

    assert len(db.scalars(select(User)).all()) == 1
    assert len(db.scalars(select(OAuthAccount)).all()) == 1


def test_unverified_provider_email_is_refused_and_creates_nothing(db, settings):
    with pytest.raises(OAuthEmailNotVerified):
        auth_service.login_with_provider(
            db, settings, google_profile(email_verified=False), None, None
        )

    assert db.scalars(select(User)).all() == []
    assert db.scalars(select(OAuthAccount)).all() == []


def test_unverified_provider_email_does_not_verify_an_existing_account(db, settings, sender):
    auth_service.register(db, settings, sender, "carol@example.com", "a-password-123")

    with pytest.raises(OAuthEmailNotVerified):
        auth_service.login_with_provider(
            db, settings, google_profile(email_verified=False), None, None
        )

    assert db.scalar(select(User)).is_verified is False
    assert db.scalars(select(OAuthAccount)).all() == []
