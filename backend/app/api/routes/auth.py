from functools import partial
from typing import Annotated
from urllib.parse import urlencode

from authlib.integrations.base_client import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.oauth import (
    PROVIDER_LABELS,
    PROVIDERS,
    build_oauth,
    callback_url,
    fetch_profile,
    is_configured,
)
from app.auth.passwords import PasswordPolicyError
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.auth import (
    EmailRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service
from app.services.auth_service import (
    InvalidCredentials,
    InvalidToken,
    OAuthEmailNotVerified,
    TokenPair,
)
from app.services.email import EmailSender, get_email_sender

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_sender(settings: SettingsDep) -> EmailSender:
    return get_email_sender(settings)


SenderDep = Annotated[EmailSender, Depends(get_sender)]


def get_oauth(settings: SettingsDep) -> OAuth:
    return build_oauth(settings)


OAuthDep = Annotated[OAuth, Depends(get_oauth)]


def _cookie_path(settings: Settings) -> str:
    return f"{settings.api_v1_prefix}/auth"


def _set_refresh_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path=_cookie_path(settings),
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=_cookie_path(settings),
        httponly=True,
        secure=True,
        samesite="lax",
    )


def _check_origin(request: Request, settings: Settings) -> None:
    # Browsers send Origin on cross-site POSTs. Reject origins we don't trust.
    # Requests without an Origin header (non-browser clients) are allowed.
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origin_list:
        raise HTTPException(status_code=403, detail="Origin not allowed.")


def _token_response(pair: TokenPair, response: Response, settings: Settings) -> TokenResponse:
    _set_refresh_cookie(response, settings, pair.refresh_token)
    return TokenResponse(access_token=pair.access_token, expires_in=pair.expires_in)


@router.post("/register", status_code=202, response_model=MessageResponse)
def register(
    body: RegisterRequest,
    db: DbSession,
    settings: SettingsDep,
    sender: SenderDep,
) -> MessageResponse:
    try:
        auth_service.register(db, settings, sender, body.email, body.password, body.name)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MessageResponse(message="Check your email for a link to verify your account.")


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: SettingsDep,
) -> TokenResponse:
    try:
        pair = auth_service.login(
            db,
            settings,
            body.email,
            body.password,
            request.headers.get("user-agent"),
            request.client.host if request.client else None,
        )
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="Invalid email or password.") from exc
    return _token_response(pair, response, settings)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse | JSONResponse:
    _check_origin(request, settings)
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    try:
        pair = auth_service.refresh(
            db,
            settings,
            refresh_token,
            request.headers.get("user-agent"),
            request.client.host if request.client else None,
        )
    except InvalidToken:
        failed = JSONResponse({"detail": "Session expired. Sign in again."}, status_code=401)
        _clear_refresh_cookie(failed, settings)
        return failed
    response = JSONResponse(
        TokenResponse(access_token=pair.access_token, expires_in=pair.expires_in).model_dump()
    )
    _set_refresh_cookie(response, settings, pair.refresh_token)
    return response


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    _check_origin(request, settings)
    if refresh_token is not None:
        auth_service.logout(db, refresh_token)
    response = Response(status_code=204)
    _clear_refresh_cookie(response, settings)
    return response


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(body: TokenRequest, db: DbSession) -> MessageResponse:
    try:
        auth_service.verify_email(db, body.token)
    except InvalidToken as exc:
        raise HTTPException(
            status_code=400, detail="This verification link is invalid or has expired."
        ) from exc
    return MessageResponse(message="Your email is verified.")


@router.post("/resend-verification", status_code=202, response_model=MessageResponse)
def resend_verification(
    body: EmailRequest,
    db: DbSession,
    settings: SettingsDep,
    sender: SenderDep,
) -> MessageResponse:
    auth_service.resend_verification(db, settings, sender, body.email)
    return MessageResponse(message="If that account needs verifying, a new link is on its way.")


@router.post("/forgot-password", status_code=202, response_model=MessageResponse)
def forgot_password(
    body: EmailRequest,
    db: DbSession,
    settings: SettingsDep,
    sender: SenderDep,
) -> MessageResponse:
    auth_service.request_password_reset(db, settings, sender, body.email)
    return MessageResponse(message="If that email has an account, a reset link is on its way.")


def _oauth_client(oauth: OAuth, provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown sign-in provider.")
    return getattr(oauth, provider)


def _oauth_error_redirect(settings: Settings, message: str) -> RedirectResponse:
    query = urlencode({"error": message})
    return RedirectResponse(f"{settings.frontend_base_url}/login?{query}", status_code=302)


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    request: Request,
    settings: SettingsDep,
    oauth: OAuthDep,
) -> Response:
    client = _oauth_client(oauth, provider)
    if not is_configured(settings, provider):
        return _oauth_error_redirect(
            settings, f"{PROVIDER_LABELS[provider]} sign-in isn't set up yet."
        )
    return await client.authorize_redirect(request, callback_url(settings, provider))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    oauth: OAuthDep,
) -> Response:
    client = _oauth_client(oauth, provider)
    label = PROVIDER_LABELS[provider]
    if not is_configured(settings, provider):
        return _oauth_error_redirect(settings, f"{label} sign-in isn't set up yet.")
    try:
        token = await client.authorize_access_token(request)
        profile = await fetch_profile(client, provider, token)
    except OAuthError:
        return _oauth_error_redirect(settings, f"Couldn't sign in with {label}. Try again.")

    try:
        pair = await run_in_threadpool(
            partial(
                auth_service.login_with_provider,
                db,
                settings,
                profile,
                request.headers.get("user-agent"),
                request.client.host if request.client else None,
            )
        )
    except OAuthEmailNotVerified:
        return _oauth_error_redirect(
            settings, f"Your {label} email isn't verified, so we can't sign you in with it."
        )

    response = RedirectResponse(f"{settings.frontend_base_url}/", status_code=302)
    _set_refresh_cookie(response, settings, pair.refresh_token)
    return response


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: DbSession) -> MessageResponse:
    try:
        auth_service.reset_password(db, body.token, body.password)
    except InvalidToken as exc:
        raise HTTPException(
            status_code=400, detail="This reset link is invalid or has expired."
        ) from exc
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MessageResponse(message="Your password has been reset. Sign in with the new one.")
