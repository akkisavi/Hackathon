"""Production showcase checks, isolated from local-demo settings."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_bundle_matches_every_source_raster():
    import json
    import numpy as np
    import rasterio
    from app.processing.water_bundle import read_array, verify_bundle
    from app.processing.water import change_masks
    verify_bundle()
    count = 0
    for model in (ROOT / "ml/models/water").glob("*.json"):
        data = json.loads(model.read_text())
        previous = None
        for row in data.get("observations", []):
            packed = read_array(model.stem, row["date"])
            raw = ROOT / "data/water" / model.stem / f"{row['date']}.tif"
            if raw.exists():
                with rasterio.open(raw) as source:
                    original = source.read(1)
                assert np.array_equal(packed, original)
                assert int((packed == 1).sum()) == round(row["open_water_km2"] / .0009)
                if previous is not None:
                    for a, b in zip(change_masks(previous[0], original), change_masks(previous[1], packed)):
                        assert np.array_equal(a, b)
                previous = original, packed
            count += 1
    assert count == 341


def test_showcase_without_raw_data_and_with_session_isolation():
    code = r'''
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1 import water
from app.processing.change_fixtures import render_fixture
from app.processing.change import encode_png
water.DATA_DIR = Path("/nonexistent-raw-data")
with TestClient(app, base_url="https://orbit.example") as client:
    assert "sqlalchemy" not in sys.modules
    assert client.get("/health").json()["showcase"] is True
    assert client.get("/api/v1/capabilities").json()["fixtures"] is True
    for site in client.get("/api/v1/water/sites").json():
        site_id = site["id"]
        observations = client.get(f"/api/v1/water/sites/{site_id}/observations").json()["observations"]
        for row in (observations[0], observations[-1]):
            prefix = f"/api/v1/water/sites/{site_id}"
            result = client.get(prefix + "/assessment", params={"date":row["date"]})
            assert result.status_code == 200, result.text
            assert result.json()["model_status"] == "experimental"
            assert result.json()["forecast"] is None
            image = client.get(prefix + "/image", params={"date":row["date"]})
            assert image.content.startswith(b"\x89PNG".decode("unicode_escape").encode("latin1"))
    assert client.get("/api/v1/change/thermal").status_code == 200
    assert client.get("/api/v1/change/fixtures").status_code == 200
    assert client.post("/api/v1/change/analyze", files={"before":("a.png",b"invalid"),"after":("b.png",b"invalid")}).status_code == 422
    payload = encode_png(render_fixture("flood", 0))
    response = client.post("/api/v1/change/analyze", files={"before":("a.png",payload,"image/png"),"after":("b.png",payload,"image/png")})
    assert response.status_code == 200, response.text
    analysis_id = response.json()["analysis_id"]
    report = client.post("/api/v1/change/report", json={"analysis_id":analysis_id})
    assert report.json()["report_mode"] == "local"
    with TestClient(app, base_url="https://orbit.example") as stranger:
        assert stranger.post("/api/v1/change/report", json={"analysis_id":analysis_id}).status_code == 404
    assert client.post("/api/v1/change/report",json={"analysis_id":analysis_id},headers={"Origin":"https://attacker.example"}).status_code == 403
    for i in range(12):
        last = client.post("/api/v1/change/report",json={"analysis_id":analysis_id})
    assert last.status_code == 429
    assert client.get("/api/v1/does-not-exist").status_code == 404
    for path in ("/orbit", "/orbit/water", "/orbit/thermal"):
        page = client.get(path)
        assert page.status_code == 200 and "<html" in page.text
    assert client.get("/assets/missing.js").status_code == 404
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "backend",
        env={**os.environ,"ORBIT_SHOWCASE":"true","ORBIT_DEMO":"false","SERVE_FRONTEND":"true"}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_corrupt_bundle_fails_readiness(tmp_path, monkeypatch):
    import json
    import pytest
    from app.processing import water_bundle
    path = tmp_path / "bad.npz"
    path.write_bytes(b"bad")
    (tmp_path / "manifest.json").write_text(json.dumps({"files":{"bad.npz":"wrong"},"observations":{}}))
    water_bundle.manifest.cache_clear()
    monkeypatch.setattr(water_bundle, "BUNDLE", tmp_path)
    try:
        with pytest.raises(RuntimeError, match="checksum"):
            water_bundle.verify_bundle()
        path.unlink()
        with pytest.raises(FileNotFoundError):
            water_bundle.verify_bundle()
    finally:
        water_bundle.manifest.cache_clear()
