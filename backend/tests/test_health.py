from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.session import build_engine, get_db
from app.main import create_app


def test_liveness_returns_ok():
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_endpoint_returns_503_when_database_is_unreachable():
    engine = build_engine("postgresql+psycopg://user:pass@127.0.0.1:1/unreachable")
    session = sessionmaker(bind=engine)()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    response = TestClient(app).get("/api/v1/health/db")

    session.close()
    engine.dispose()
    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"]
