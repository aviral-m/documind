import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health import DatabaseHealthResponse, LivenessResponse
from app.services.health import check_database

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get("/db", response_model=DatabaseHealthResponse)
def database_health(db: DbSession) -> DatabaseHealthResponse:
    try:
        latency_ms = check_database(db)
    except SQLAlchemyError as exc:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=503,
            detail=(
                "Database is unreachable. If Neon was idle it may still be waking up; "
                "try again shortly."
            ),
        ) from exc
    return DatabaseHealthResponse(
        status="ok", database="connected", latency_ms=round(latency_ms, 1)
    )
