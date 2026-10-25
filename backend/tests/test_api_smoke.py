"""No-DB API checks: app boots and every route is wired."""
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.dependencies import get_current_user_or_api_key
from app.core.db import get_db

client = TestClient(app)


@pytest.fixture
def authenticated_client():
    # Validate request shapes after authentication, without contacting a DB.
    app.dependency_overrides[get_current_user_or_api_key] = lambda: object()
    app.dependency_overrides[get_db] = lambda: None
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_all_routes_registered():
    paths = {r.path for r in app.routes}
    for p in (
        "/api/v1/hotspots/", "/api/v1/sources/", "/api/v1/sources/{source_id}",
        "/api/v1/ingest/", "/api/v1/query/", "/api/v1/alerts/",
        "/api/v1/infra/", "/api/v1/infra/counts", "/api/v1/export/",
    ):
        assert p in paths


def test_export_rejects_bad_format(authenticated_client):
    assert authenticated_client.get("/api/v1/export/?format=pdf").status_code == 422


def test_query_rejects_empty_body(authenticated_client):
    # missing required {"q": ...} -> 422, proves the route is live (not 501)
    assert authenticated_client.post("/api/v1/query/", json={}).status_code == 422


def test_original_routes_still_require_authentication():
    assert client.get("/api/v1/export/?format=geojson").status_code == 401
    assert client.post("/api/v1/query/", json={"q": "wildfires"}).status_code == 401
    assert client.post("/api/v1/change/report", json={"analysis_id": "unknown"}).status_code == 401
