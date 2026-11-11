import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import engine

logger = logging.getLogger("documind")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("DocuMind backend starting (env=%s)", get_settings().app_env)
    yield
    engine.dispose()
    logger.info("DocuMind backend stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(title="DocuMind API", version="0.1.0", lifespan=lifespan)
    # Only used to hold the OAuth state during the sign-in handshake, not for user sessions.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.auth_secret,
        session_cookie="documind_oauth",
        max_age=600,
        same_site="lax",
        https_only=settings.app_env != "development",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
