"""Check the public HTTP contract and interactive documentation route."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_contract():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_documentation_and_schema():
    with TestClient(app) as client:
        docs = client.get("/docs")
        schema = client.get("/openapi.json")
    assert docs.status_code == 200
    assert "swagger-ui" in docs.text
    assert schema.status_code == 200
    assert "/health" in schema.json()["paths"]


def test_unimplemented_science_route_is_not_a_fake_result():
    with TestClient(app) as client:
        response = client.get("/targets/BRCA1")
    assert response.status_code == 404
