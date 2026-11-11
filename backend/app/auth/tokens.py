import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

ACCESS_TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"


def create_access_token(user_id: uuid.UUID, secret: str, ttl_minutes: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, secret, algorithm=ACCESS_TOKEN_ALGORITHM)


def decode_access_token(token: str, secret: str) -> uuid.UUID:
    payload = jwt.decode(token, secret, algorithms=[ACCESS_TOKEN_ALGORITHM])
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Wrong token type")
    return uuid.UUID(payload["sub"])


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
