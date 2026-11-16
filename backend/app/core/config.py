from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

PLACEHOLDER_AUTH_SECRET = "change-me-to-a-long-random-string"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    test_database_url: str = ""
    cors_origins: str = "http://localhost:5173"
    cloudinary_url: str = ""
    max_upload_mb: int = 10
    max_pages: int = 500
    frontend_base_url: str = "http://localhost:5173"

    gemini_api_key: str = ""
    embedding_model: str = "gemini-embedding-001"
    # Must match the vector(768) column in document_chunks. Changing it needs a migration.
    embedding_dimensions: Literal[768] = 768
    embedding_batch_size: int = Field(default=100, ge=1, le=100)
    chunk_target_chars: int = Field(default=1000, ge=100)
    chunk_overlap_chars: int = Field(default=150, ge=0)

    auth_secret: str = PLACEHOLDER_AUTH_SECRET
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    email_verification_ttl_hours: int = 24
    password_reset_ttl_minutes: int = 60

    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:5173"

    email_backend: Literal["console", "smtp"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @model_validator(mode="after")
    def check_auth_secret(self) -> "Settings":
        if self.app_env != "development" and (
            self.auth_secret == PLACEHOLDER_AUTH_SECRET or len(self.auth_secret) < 32
        ):
            raise ValueError("AUTH_SECRET must be a random string of at least 32 characters")
        if self.chunk_overlap_chars >= self.chunk_target_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_TARGET_CHARS")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
