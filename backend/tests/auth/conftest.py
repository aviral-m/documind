import re
from dataclasses import dataclass, field

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.core.config import Settings
from app.db.base import Base

TOKEN_PATTERN = re.compile(r"token=([A-Za-z0-9_\-]+)")


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str

    @property
    def token(self) -> str:
        match = TOKEN_PATTERN.search(self.body)
        assert match, "email body has no token link"
        return match.group(1)


@dataclass
class FakeSender:
    sent: list[SentEmail] = field(default_factory=list)

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append(SentEmail(to=to, subject=subject, body=body))


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
def sender() -> FakeSender:
    return FakeSender()


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
