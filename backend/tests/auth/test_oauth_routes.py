import asyncio
from urllib.parse import parse_qs, urlparse

import pytest
from authlib.integrations.base_client import OAuthError
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes.auth import get_oauth
from app.auth.oauth import build_oauth, fetch_profile
from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app
from app.models import OAuthAccount, User


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeProviderClient:
    def __init__(self, responses=None, token_error=None):
        self.responses = responses or {}
        self.token_error = token_error

    async def authorize_access_token(self, request):
        if self.token_error:
            raise self.token_error
        return {"access_token": "provider-token"}

    async def get(self, url, token=None):
        return FakeResponse(self.responses[url])


class FakeOAuth:
    def __init__(self, google=None, github=None):
        self.google = google
        self.github = github


GOOGLE_USERINFO = {
    "sub": "google-456",
    "email": "dana@example.com",
    "email_verified": True,
    "name": "Dana",
    "picture": "https://img.example/dana.png",
}


@pytest.fixture
def configured_settings(settings):
    return settings.model_copy(
        update={
            "google_client_id": "google-client-id",
            "google_client_secret": "google-client-secret",
            "github_client_id": "github-client-id",
            "github_client_secret": "github-client-secret",
        }
    )


@pytest.fixture
def client(db, configured_settings):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: configured_settings
    return TestClient(app)


def test_authorize_redirects_to_google_with_the_configured_callback(client):
    response = client.get("/api/v1/auth/oauth/google/authorize", follow_redirects=False)

    assert response.status_code == 302
    target = urlparse(response.headers["location"])
    query = parse_qs(target.query)
    assert f"{target.scheme}://{target.netloc}{target.path}" == (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )
    assert query["client_id"] == ["google-client-id"]
    assert query["redirect_uri"] == ["http://localhost:5173/api/v1/auth/oauth/google/callback"]
    assert query["state"][0]


def test_google_client_loads_its_signing_keys_from_openid_metadata(configured_settings):
    oauth = build_oauth(configured_settings)

    assert oauth.google._server_metadata_url == (
        "https://accounts.google.com/.well-known/openid-configuration"
    )


def test_authorize_redirects_to_github_with_the_configured_callback(client):
    response = client.get("/api/v1/auth/oauth/github/authorize", follow_redirects=False)

    target = urlparse(response.headers["location"])
    assert target.netloc == "github.com"
    assert parse_qs(target.query)["redirect_uri"] == [
        "http://localhost:5173/api/v1/auth/oauth/github/callback"
    ]


def test_authorize_without_credentials_returns_to_login_with_a_message(db, settings):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).get(
        "/api/v1/auth/oauth/google/authorize", follow_redirects=False
    )

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == "http://app.test/login"
    assert parse_qs(location.query)["error"] == ["Google sign-in isn't set up yet."]


def test_unknown_provider_is_not_found(client):
    response = client.get("/api/v1/auth/oauth/apple/authorize", follow_redirects=False)

    assert response.status_code == 404


def test_callback_signs_in_and_sets_the_refresh_cookie(db, client, configured_settings):
    fake = FakeOAuth(google=FakeProviderClient({"userinfo": GOOGLE_USERINFO}))
    client.app.dependency_overrides[get_oauth] = lambda: fake

    response = client.get(
        "/api/v1/auth/oauth/google/callback?code=abc&state=xyz", follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "http://app.test/"
    assert "refresh_token=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    user = db.scalar(select(User).where(User.email == "dana@example.com"))
    assert user is not None
    assert user.is_verified is True
    assert db.scalar(select(OAuthAccount)).provider == "google"


def test_callback_user_denying_access_returns_to_login_with_a_message(db, client):
    fake = FakeOAuth(
        google=FakeProviderClient(token_error=OAuthError(error="access_denied"))
    )
    client.app.dependency_overrides[get_oauth] = lambda: fake

    response = client.get(
        "/api/v1/auth/oauth/google/callback?error=access_denied", follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith("http://app.test/login?error=")
    assert "set-cookie" not in response.headers
    assert db.scalars(select(User)).all() == []


def test_callback_with_unverified_provider_email_is_refused(db, client):
    unverified = {**GOOGLE_USERINFO, "email_verified": False}
    fake = FakeOAuth(google=FakeProviderClient({"userinfo": unverified}))
    client.app.dependency_overrides[get_oauth] = lambda: fake

    response = client.get(
        "/api/v1/auth/oauth/google/callback?code=abc&state=xyz", follow_redirects=False
    )

    assert response.status_code == 302
    assert "verified" in response.headers["location"]
    assert "set-cookie" not in response.headers
    assert db.scalars(select(User)).all() == []


def test_github_profile_uses_the_primary_email_and_its_verified_flag():
    client = FakeProviderClient(
        {
            "user": {"id": 99, "name": "Eve", "avatar_url": "https://img.example/eve.png"},
            "user/emails": [
                {"email": "old@example.com", "primary": False, "verified": True},
                {"email": "eve@example.com", "primary": True, "verified": True},
            ],
        }
    )

    profile = asyncio.run(fetch_profile(client, "github", token={}))

    assert profile.provider_account_id == "99"
    assert profile.email == "eve@example.com"
    assert profile.email_verified is True
    assert profile.name == "Eve"
