import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import build_engine, get_db
from app.main import create_app
from app.services.health import check_database

pytestmark = pytest.mark.integration


@pytest.fixture
def test_session():
    url = get_settings().test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = build_engine(url)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_check_database_runs_against_real_database(test_session):
    assert check_database(test_session) >= 0


def test_db_endpoint_reports_connected(test_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: test_session

    response = TestClient(app).get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json()["database"] == "connected"
