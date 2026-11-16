import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models.document_chunk import EMBEDDING_DIMENSIONS


def make(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "database_url": "postgresql+psycopg://user:pass@host/db?sslmode=require",
        "auth_secret": "test-secret-that-is-long-enough-for-hs256-0123456789",
    }
    values.update(overrides)
    return Settings(**values)


def test_default_embedding_settings_match_the_database_column():
    settings = make()

    assert settings.embedding_model == "gemini-embedding-001"
    assert settings.embedding_dimensions == EMBEDDING_DIMENSIONS == 768
    assert settings.chunk_target_chars == 1000
    assert settings.chunk_overlap_chars == 150


def test_a_dimension_other_than_the_column_size_is_rejected():
    with pytest.raises(ValidationError):
        make(embedding_dimensions=1536)


def test_overlap_must_be_smaller_than_the_chunk_size():
    with pytest.raises(ValidationError):
        make(chunk_target_chars=200, chunk_overlap_chars=200)
