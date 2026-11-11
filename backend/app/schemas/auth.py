import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.auth.passwords import MAX_PASSWORD_LENGTH


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None
    is_verified: bool


class MessageResponse(BaseModel):
    message: str
