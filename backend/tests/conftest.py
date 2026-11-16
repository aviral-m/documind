import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.core.config import Settings
from app.db.base import Base
from tests.fakes import FakeEmbedder


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@host/db?sslmode=require",
        auth_secret="test-secret-that-is-long-enough-for-hs256-0123456789",
        frontend_base_url="http://app.test",
        cors_origins="http://localhost:5173",
    )


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session: Session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    engine.dispose()
