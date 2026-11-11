from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.tokens import decode_access_token
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Not signed in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials, settings.auth_secret)
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise unauthorized from exc
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_verified_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Verify your email to continue.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
VerifiedUser = Annotated[User, Depends(require_verified_user)]
