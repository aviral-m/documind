import uuid

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.routes.documents import get_session_factory
from app.auth.tokens import create_access_token
from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app
from app.models import User


@pytest.fixture
def storage_settings(settings, tmp_path):
    return settings.model_copy(update={"storage_dir": str(tmp_path)})


@pytest.fixture
def session_factory(db):
    return sessionmaker(bind=db.get_bind(), expire_on_commit=False)


@pytest.fixture
def client(db, storage_settings, session_factory):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: storage_settings
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    return TestClient(app)


@pytest.fixture
def make_user(db):
    def _make(verified: bool = True) -> User:
        user = User(email=f"{uuid.uuid4()}@example.com", is_verified=verified)
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def auth_headers(storage_settings):
    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(user.id, storage_settings.auth_secret, 15)
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def make_pdf():
    def _make(pages: list[str]) -> bytes:
        document = pymupdf.open()
        for text in pages:
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text)
        data = document.tobytes()
        document.close()
        return data

    return _make
