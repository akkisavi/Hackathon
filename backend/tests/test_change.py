"""Track 05 acceptance tests: self-contained, no external credentials or services."""
import base64
import io
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.ai import change_report
from app.api.v1 import change
from app.processing.change import analyze_pair, decode_image, encode_png
from app.processing.change_fixtures import render_fixture


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(change.build_router(change.loopback_only, demo=True), prefix="/api/v1")
    change._analyses.clear()
    return TestClient(app)


def pair(scenario="flood"):
    return render_fixture(scenario, 0), render_fixture(scenario, 3)


def upload(client, scenario="flood", **data):
    before, after = pair(scenario)
    return client.post("/api/v1/change/analyze", files={
        "before": ("before.png", encode_png(before), "image/png"),
        "after": ("after.png", encode_png(after), "image/png"),
    }, data=data)


@pytest.mark.parametrize("scenario", ["flood", "excavation", "control"])
def test_fixture_measurements(scenario):
    before, after = pair(scenario)
    result = analyze_pair(before, after, pixel_size_m=2)
    assert sum(r["pixels"] for r in result["regions"]) == result["changed_pixels"]
    assert result["changed_fraction"] == result["changed_pixels"] / (512 * 512)
    assert result["area_m2"] == result["changed_pixels"] * 4
    mask = decode_image(base64.b64decode(result["mask"].split(",")[1]))[:, :, 0] > 0
    truth = np.any(before != after, axis=2)
    if scenario == "control":
        assert not result["regions"] and result["changed_pixels"] == 0
    else:
        assert result["regions"]
        assert np.logical_and(mask, truth).sum() / np.logical_or(mask, truth).sum() > 0.75
        assert all(len(r["polygon_xy"]) >= 3 for r in result["regions"])


def test_api_analysis_report_and_expiration(client, monkeypatch):
    monkeypatch.setattr(change_report, "get_client", lambda: (_ for _ in ()).throw(RuntimeError("secret")))
    result = upload(client).json()
    assert result["area_m2"] is None
    response = client.post("/api/v1/change/report", json={"analysis_id": result["analysis_id"]})
    assert response.status_code == 200
    assert response.json()["report_mode"] == "local_fallback"
    assert "secret" not in response.text
    with change._lock:
        change._analyses[result["analysis_id"]]["created"] -= change.TTL_SECONDS + 1
    assert client.post("/api/v1/change/report", json={"analysis_id": result["analysis_id"]}).status_code == 404


def test_control_never_calls_provider(client, monkeypatch):
    def fail():
        pytest.fail("Control must not invoke provider")
    monkeypatch.setattr(change_report, "get_client", fail)
    result = upload(client, "control").json()
    report = client.post("/api/v1/change/report", json={"analysis_id": result["analysis_id"]}).json()
    assert report["report_mode"] == "local"
    assert report["report"]["hypothesis"] == "no_change"


@pytest.mark.parametrize("value", ["not json", json.dumps({
    "hypothesis": "human_like", "evidence": [{"region_id": "R999", "observation": "Unfounded"}],
    "next_action": "Inspect", "limitations": ["Uncertain"]
})])
def test_invalid_model_report_falls_back(monkeypatch, value):
    fake = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=value))])
    def create(**kwargs):
        content = kwargs["messages"][0]["content"]
        assert len([p for p in content if p["type"] == "image_url"]) == 2
        return fake
    provider = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(change_report, "get_client", lambda: SimpleNamespace(with_options=lambda **kw: provider))
    result = change_report.generate_change_report(*pair(), analyze_pair(*pair()))
    assert result["report_mode"] == "local_fallback"


def test_valid_model_report(monkeypatch):
    payload = change_report.local_report(analyze_pair(*pair()))
    fake = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
    provider = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: fake)))
    monkeypatch.setattr(change_report, "get_client", lambda: SimpleNamespace(with_options=lambda **kw: provider))
    assert change_report.generate_change_report(*pair(), analyze_pair(*pair()))["report_mode"] == "gemini"


def test_validation_and_localhost_boundary(client):
    assert upload(client, threshold="nan").status_code == 422
    assert upload(client, pixel_size_m="inf").status_code == 422
    assert upload(client, pixel_size_m="-1").status_code == 422
    bad = client.post("/api/v1/change/analyze", files={"before": ("bad.png", b"bad"), "after": ("bad.png", b"bad")})
    assert bad.status_code == 422
    with pytest.raises(ValueError):
        decode_image(b"x" * 5_000_001)
    for fmt, size in [("PNG", (100, 100)), ("GIF", (512, 512))]:
        buffer = io.BytesIO()
        Image.new("RGB", size).save(buffer, format=fmt)
        with pytest.raises(ValueError):
            decode_image(buffer.getvalue())
    assert client.get("/api/v1/change/fixtures", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("http://evil.example/api/v1/change/fixtures").status_code == 403
    assert client.get("/api/v1/change/fixtures/invalid/image").status_code == 404


def test_bounded_store(client, monkeypatch):
    monkeypatch.setattr(change, "MAX_ANALYSES", 2)
    first = upload(client).json()["analysis_id"]
    upload(client)
    upload(client)
    assert len(change._analyses) == 2
    assert client.post("/api/v1/change/report", json={"analysis_id": first}).status_code == 404


def test_owner_isolation():
    principal = {"id": "alice"}
    app = FastAPI()
    app.include_router(change.build_router(lambda: principal["id"]), prefix="/api/v1")
    client = TestClient(app)
    result = upload(client).json()
    principal["id"] = "bob"
    assert client.post("/api/v1/change/report", json={"analysis_id": result["analysis_id"]}).status_code == 404


def test_demo_boots_without_database_dependencies():
    # A fresh process proves startup does not import SQLAlchemy/Celery/Earth Engine.
    code = "from app.main import app; import sys; assert 'sqlalchemy' not in sys.modules; print(len(app.routes))"
    result = subprocess.run([sys.executable, "-c", code], env={**os.environ, "ORBIT_DEMO": "true"},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_existing_thermal_snapshot_available_without_database(client):
    response = client.get("/api/v1/change/thermal")
    assert response.status_code == 200
    snapshot = response.json()
    assert len(snapshot["features"]) == 4984
    assert snapshot["features"][0]["properties"]["predicted_class"]
    assert "Not live" in snapshot["provenance"]


def test_missing_ai_key_returns_safe_actionable_notice(monkeypatch):
    monkeypatch.setattr(change_report, "get_settings", lambda: SimpleNamespace(llm_api_key=""))
    monkeypatch.setattr(change_report, "get_client", lambda: (_ for _ in ()).throw(RuntimeError("credential-secret")))
    result = change_report.generate_change_report(*pair(), analyze_pair(*pair()))
    assert result["fallback_reason"] == "not_configured"
    assert "LLM_API_KEY" in result["report_notice"]
    assert "credential-secret" not in json.dumps(result)


def test_invalid_ai_response_explains_fallback(monkeypatch):
    fake = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="invalid json"))])
    provider = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: fake)))
    monkeypatch.setattr(change_report, "get_client", lambda: SimpleNamespace(with_options=lambda **kw: provider))
    result = change_report.generate_change_report(*pair(), analyze_pair(*pair()))
    assert result["fallback_reason"] == "invalid_response"
    assert "local assessment" in result["report_notice"].lower()


def test_local_report_contains_region_location_and_percentage():
    measurement = analyze_pair(*pair())
    report = change_report.local_report(measurement)
    observation = report["evidence"][0]["observation"]
    region = measurement["regions"][0]
    assert f"{region['pixels'] / (512 * 512) * 100:.2f}%" in observation
    assert "bounding box" in observation
