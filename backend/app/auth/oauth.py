from dataclasses import dataclass
from typing import Any

from authlib.integrations.base_client import OAuthError
from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App

from app.core.config import Settings

PROVIDERS = ("google", "github")
PROVIDER_LABELS = {"google": "Google", "github": "GitHub"}


@dataclass(frozen=True)
class ProviderProfile:
    provider: str
    provider_account_id: str
    email: str
    email_verified: bool
    name: str | None
    avatar_url: str | None


def build_oauth(settings: Settings) -> OAuth:
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        api_base_url="https://openidconnect.googleapis.com/v1/",
        client_kwargs={"scope": "openid email profile"},
    )
    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )
    return oauth


def is_configured(settings: Settings, provider: str) -> bool:
    if provider == "google":
        return bool(settings.google_client_id and settings.google_client_secret)
    return bool(settings.github_client_id and settings.github_client_secret)


def callback_url(settings: Settings, provider: str) -> str:
    # Built from settings, not the request, because the Vite proxy rewrites the Host header.
    base = settings.oauth_redirect_base_url.rstrip("/")
    return f"{base}{settings.api_v1_prefix}/auth/oauth/{provider}/callback"


async def fetch_profile(client: StarletteOAuth2App, provider: str, token: Any) -> ProviderProfile:
    if provider == "google":
        data = (await client.get("userinfo", token=token)).json()
        if not data.get("sub") or not data.get("email"):
            raise OAuthError(description="Google did not return an account email.")
        return ProviderProfile(
            provider=provider,
            provider_account_id=str(data["sub"]),
            email=str(data["email"]),
            email_verified=bool(data.get("email_verified")),
            name=data.get("name"),
            avatar_url=data.get("picture"),
        )

    user = (await client.get("user", token=token)).json()
    emails = (await client.get("user/emails", token=token)).json()
    primary = next((entry for entry in emails if entry.get("primary")), None)
    if not user.get("id") or primary is None:
        raise OAuthError(description="GitHub did not return an account email.")
    return ProviderProfile(
        provider=provider,
        provider_account_id=str(user["id"]),
        email=str(primary["email"]),
        email_verified=bool(primary.get("verified")),
        name=user.get("name"),
        avatar_url=user.get("avatar_url"),
    )
