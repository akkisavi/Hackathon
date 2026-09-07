"""No-DB API checks: app boots and every route is wired."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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


def test_export_rejects_bad_format():
    assert client.get("/api/v1/export/?format=pdf").status_code == 422


def test_query_rejects_empty_body():
    # missing required {"q": ...} -> 422, proves the route is live (not 501)
    assert client.post("/api/v1/query/", json={}).status_code == 422
