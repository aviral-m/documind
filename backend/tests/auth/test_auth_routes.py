import pytest
from fastapi.testclient import TestClient

from app.api.routes.auth import get_sender
from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app

EMAIL = "bob@example.com"
PASSWORD = "correct-horse-battery"


def cookie(value: str) -> dict[str, str]:
    return {"Cookie": f"refresh_token={value}"}


@pytest.fixture
def client(db, settings, sender):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_sender] = lambda: sender
    return TestClient(app)


def test_full_email_password_flow(client, sender):
    response = client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 202

    response = client.post("/api/v1/auth/verify-email", json={"token": sender.sent[-1].token})
    assert response.status_code == 200

    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    access = response.json()["access_token"]
    cookie_header = response.headers["set-cookie"]
    assert "refresh_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "Path=/api/v1/auth" in cookie_header
    refresh_value = response.cookies["refresh_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL
    assert response.json()["is_verified"] is True

    response = client.post("/api/v1/auth/refresh", headers=cookie(refresh_value))
    assert response.status_code == 200
    rotated = response.cookies["refresh_token"]
    assert rotated != refresh_value

    response = client.post("/api/v1/auth/refresh", headers=cookie(refresh_value))
    assert response.status_code == 401

    response = client.post("/api/v1/auth/logout", headers=cookie(rotated))
    assert response.status_code == 204

    response = client.post("/api/v1/auth/refresh", headers=cookie(rotated))
    assert response.status_code == 401


def test_me_without_token_is_unauthorized(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_login_error_does_not_reveal_which_part_was_wrong(client, sender):
    client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})

    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": "wrong-password-1"}
    )
    unknown_email = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_refresh_from_untrusted_origin_is_forbidden(client):
    response = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "https://evil.example", **cookie("anything")},
    )

    assert response.status_code == 403


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register", json={"email": EMAIL, "password": "short"}
    )

    assert response.status_code == 422


def test_invalid_verification_link_is_bad_request(client):
    response = client.post("/api/v1/auth/verify-email", json={"token": "not-a-real-token"})

    assert response.status_code == 400


def test_password_reset_route_round_trip(client, sender):
    client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    client.post("/api/v1/auth/verify-email", json={"token": sender.sent[-1].token})

    response = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 202

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": sender.sent[-1].token, "password": "a-new-valid-password"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": "a-new-valid-password"}
    )
    assert response.status_code == 200
