import pytest
from pydantic import ValidationError

from app.schemas.health import DatabaseHealthResponse


def test_database_health_serializes_to_expected_shape():
    payload = DatabaseHealthResponse(
        status="ok", database="connected", latency_ms=12.5
    ).model_dump()

    assert payload == {"status": "ok", "database": "connected", "latency_ms": 12.5}


def test_database_health_rejects_unknown_status():
    with pytest.raises(ValidationError):
        DatabaseHealthResponse(status="down", database="connected", latency_ms=1)
