import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.oauth import ProviderProfile
from app.auth.passwords import hash_password, validate_password, verify_password
from app.auth.tokens import create_access_token, generate_opaque_token, hash_opaque_token
from app.core.config import Settings
from app.models import AuthToken, OAuthAccount, RefreshToken, User
from app.models.auth_token import RESET_PASSWORD, VERIFY_EMAIL
from app.services.email import (
    EmailSender,
    send_password_reset_email,
    send_verification_email,
)

_TIMING_PLACEHOLDER_HASH = hash_password("timing-placeholder-password")


class InvalidCredentials(Exception):
    pass


class InvalidToken(Exception):
    pass


class OAuthEmailNotVerified(Exception):
    pass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    # SQLite returns naive datetimes; Postgres returns aware ones. Treat naive as UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def _create_refresh_token(
    db: Session,
    settings: Settings,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[RefreshToken, str]:
    raw = generate_opaque_token()
    row = RefreshToken(
        user_id=user_id,
        family_id=family_id,
        token_hash=hash_opaque_token(raw),
        expires_at=_now() + timedelta(days=settings.refresh_token_ttl_days),
        user_agent=user_agent[:255] if user_agent else None,
        ip_address=ip_address[:64] if ip_address else None,
    )
    db.add(row)
    db.flush()
    return row, raw


def _issue_token_pair(
    db: Session,
    settings: Settings,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenPair:
    _, refresh_raw = _create_refresh_token(db, settings, user_id, family_id, user_agent, ip_address)
    access = create_access_token(
        user_id, settings.auth_secret, settings.access_token_ttl_minutes
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh_raw,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


def _revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def _revoke_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def _issue_auth_token(db: Session, settings: Settings, user: User, purpose: str) -> str:
    # A new link invalidates any older unused link of the same purpose.
    db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )
    if purpose == VERIFY_EMAIL:
        ttl = timedelta(hours=settings.email_verification_ttl_hours)
    else:
        ttl = timedelta(minutes=settings.password_reset_ttl_minutes)
    raw = generate_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_opaque_token(raw),
            expires_at=_now() + ttl,
        )
    )
    db.flush()
    return raw


def _find_auth_token(db: Session, raw: str, purpose: str) -> AuthToken:
    row = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == hash_opaque_token(raw),
            AuthToken.purpose == purpose,
        )
    )
    if row is None or row.used_at is not None or _aware(row.expires_at) <= _now():
        raise InvalidToken
    return row


def register(
    db: Session,
    settings: Settings,
    sender: EmailSender,
    email: str,
    password: str,
    name: str | None = None,
) -> None:
    """Creates an account if the email is new.

    Returns nothing either way, so callers can't tell whether the email was already
    registered. Existing accounts get no email.
    """
    email = normalize_email(email)
    validate_password(password, email)
    if _find_user_by_email(db, email) is not None:
        return
    user = User(email=email, hashed_password=hash_password(password), name=name)
    db.add(user)
    db.flush()
    raw = _issue_auth_token(db, settings, user, VERIFY_EMAIL)
    db.commit()
    link = f"{settings.frontend_base_url}/verify-email?token={raw}"
    send_verification_email(sender, user.email, link)


def login(
    db: Session,
    settings: Settings,
    email: str,
    password: str,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenPair:
    user = _find_user_by_email(db, email)
    if user is None or user.hashed_password is None:
        # Spend the same time hashing as a real check, so response timing doesn't reveal the email.
        verify_password(password, _TIMING_PLACEHOLDER_HASH)
        raise InvalidCredentials
    if not verify_password(password, user.hashed_password):
        raise InvalidCredentials
    pair = _issue_token_pair(db, settings, user.id, uuid.uuid4(), user_agent, ip_address)
    db.commit()
    return pair


def login_with_provider(
    db: Session,
    settings: Settings,
    profile: ProviderProfile,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenPair:
    """Signs in through Google or GitHub, creating or linking the account as needed.

    Accounts are only linked or created from an email the provider has verified, so nobody
    can take over an existing account by claiming an address they don't own.
    """
    if not profile.email_verified:
        raise OAuthEmailNotVerified

    account = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == profile.provider,
            OAuthAccount.provider_account_id == profile.provider_account_id,
        )
    )
    if account is not None:
        user = db.get(User, account.user_id)
    else:
        user = _find_user_by_email(db, profile.email)
        if user is None:
            user = User(
                email=normalize_email(profile.email),
                hashed_password=None,
                name=profile.name,
                avatar_url=profile.avatar_url,
            )
            db.add(user)
            db.flush()
        db.add(
            OAuthAccount(
                user_id=user.id,
                provider=profile.provider,
                provider_account_id=profile.provider_account_id,
            )
        )
    if user is None:
        raise InvalidToken
    user.is_verified = True
    pair = _issue_token_pair(db, settings, user.id, uuid.uuid4(), user_agent, ip_address)
    db.commit()
    return pair


def refresh(
    db: Session,
    settings: Settings,
    raw_refresh_token: str,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenPair:
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(raw_refresh_token))
    )
    if row is None:
        raise InvalidToken
    now = _now()
    if row.revoked_at is not None or row.replaced_by_id is not None:
        # A rotated or revoked token was presented again: someone else may have copied it.
        # Revoke the whole session chain so the attacker and the real user both have to sign in.
        _revoke_family(db, row.family_id)
        db.commit()
        raise InvalidToken
    if _aware(row.expires_at) <= now:
        raise InvalidToken
    user = db.get(User, row.user_id)
    if user is None:
        raise InvalidToken

    new_row, new_refresh_raw = _create_refresh_token(
        db, settings, user.id, row.family_id, user_agent, ip_address
    )
    row.replaced_by_id = new_row.id
    row.revoked_at = now
    access = create_access_token(user.id, settings.auth_secret, settings.access_token_ttl_minutes)
    db.commit()
    return TokenPair(
        access_token=access,
        refresh_token=new_refresh_raw,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


def logout(db: Session, raw_refresh_token: str) -> None:
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(raw_refresh_token))
    )
    if row is not None:
        _revoke_family(db, row.family_id)
        db.commit()


def verify_email(db: Session, raw_token: str) -> None:
    row = _find_auth_token(db, raw_token, VERIFY_EMAIL)
    user = db.get(User, row.user_id)
    if user is None:
        raise InvalidToken
    row.used_at = _now()
    user.is_verified = True
    db.commit()


def resend_verification(
    db: Session, settings: Settings, sender: EmailSender, email: str
) -> None:
    user = _find_user_by_email(db, email)
    if user is None or user.is_verified:
        return
    raw = _issue_auth_token(db, settings, user, VERIFY_EMAIL)
    db.commit()
    link = f"{settings.frontend_base_url}/verify-email?token={raw}"
    send_verification_email(sender, user.email, link)


def request_password_reset(
    db: Session, settings: Settings, sender: EmailSender, email: str
) -> None:
    user = _find_user_by_email(db, email)
    if user is None:
        return
    raw = _issue_auth_token(db, settings, user, RESET_PASSWORD)
    db.commit()
    link = f"{settings.frontend_base_url}/reset-password?token={raw}"
    send_password_reset_email(sender, user.email, link)


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    row = _find_auth_token(db, raw_token, RESET_PASSWORD)
    user = db.get(User, row.user_id)
    if user is None:
        raise InvalidToken
    # Validate before consuming the link, so a weak password doesn't use up the reset.
    validate_password(new_password, user.email)
    row.used_at = _now()
    user.hashed_password = hash_password(new_password)
    _revoke_all_for_user(db, user.id)
    db.commit()
