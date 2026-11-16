import uuid

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.routes.documents import get_file_storage, get_session_factory
from app.auth.tokens import create_access_token
from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app
from app.models import User
from app.services.embedder import get_embedder
from app.services.storage import DOWNLOAD_FAILED_MESSAGE, StorageError


class FakeStorage:
    """In-memory stand-in for CloudinaryStorage. No network."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.fail_save: str | None = None
        self.fail_download = False
        self.fail_delete = False

    def save(self, public_id: str, data: bytes) -> None:
        if self.fail_save:
            raise StorageError(self.fail_save)
        if public_id in self.files:
            raise StorageError("already exists")
        self.files[public_id] = data

    def download(self, public_id: str) -> bytes:
        if self.fail_download or public_id not in self.files:
            raise StorageError(DOWNLOAD_FAILED_MESSAGE)
        return self.files[public_id]

    def delete(self, public_id: str) -> None:
        if self.fail_delete:
            raise StorageError("Cloudinary could not delete.")
        self.files.pop(public_id, None)


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def session_factory(db):
    return sessionmaker(bind=db.get_bind(), expire_on_commit=False)


@pytest.fixture
def client(db, settings, storage, session_factory, embedder):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_embedder] = lambda: embedder
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
def auth_headers(settings):
    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(user.id, settings.auth_secret, 15)
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
