"""Reproducible illustrative overhead scenes, never claimed as satellite captures."""
from functools import lru_cache
import json
from pathlib import Path

import cv2
import numpy as np

FIXTURES = [
    {"id": "flood", "name": "River overflow", "location": "Brahmaputra basin · illustrative site",
     "description": "An expanding river reaches forest and agricultural land.",
     "center": [91.72, 26.18], "bbox": [91.7149, 26.1754, 91.7251, 26.1846], "color": "#227f86"},
    {"id": "excavation", "name": "Land excavation", "location": "Eastern plateau · illustrative site",
     "description": "A geometric clearing expands into a forested hillside.",
     "center": [85.32, 23.36], "bbox": [85.315, 23.3554, 85.325, 23.3646], "color": "#b5653d"},
    {"id": "control", "name": "Unchanged landscape", "location": "Reference scene · illustrative site",
     "description": "An identical image pair checks for false change detections.",
     "center": [84.99, 24.8], "bbox": [84.985, 24.7954, 84.995, 24.8046], "color": "#6a7869"},
]


@lru_cache(maxsize=12)
def render_fixture(scenario: str, frame: int = 3) -> np.ndarray:
    if scenario not in {f["id"] for f in FIXTURES} or frame not in range(4):
        raise ValueError("Unknown fixture or frame.")
    rng = np.random.default_rng(7)
    field = cv2.resize(rng.random((24, 24)).astype(np.float32), (512, 512), interpolation=cv2.INTER_CUBIC)
    fine = rng.normal(0, 5, (512, 512))
    base = np.stack([58 + field * 42 + fine, 81 + field * 48 + fine,
                     48 + field * 30 + fine], axis=2)
    image = np.clip(base, 0, 255).astype(np.uint8)
    # Small canopy crowns, farm parcels, roads and buildings establish scale.
    for _ in range(9000):
        x, y = rng.integers(0, 512, 2)
        color = tuple(int(v) for v in image[y, x] * rng.uniform(0.65, 1.18))
        cv2.circle(image, (int(x), int(y)), int(rng.integers(1, 4)), color, -1)
    for row in range(3):
        for col in range(4):
            x, y = 330 + col * 42, 340 + row * 48
            cv2.rectangle(image, (x, y), (x + 37, y + 42),
                          (118 + row * 9, 119 + col * 7, 72 + row * 5), -1)
    cv2.line(image, (0, 95), (512, 40), (166, 161, 140), 8)
    cv2.line(image, (0, 95), (512, 40), (195, 187, 161), 3)
    for x in range(35, 220, 27):
        cv2.rectangle(image, (x, 55), (x + 16, 70), (55, 60, 50), -1)
        cv2.rectangle(image, (x - 2, 52), (x + 14, 65), (181, 175, 154), -1)

    ys = np.arange(512)
    center = 275 + 32 * np.sin(ys / 65) + 16 * np.sin(ys / 133)
    width = 19 + 5 * np.sin(ys / 70)
    if scenario == "flood":
        width = width + frame * (14 + 10 * np.sin(ys / 130) ** 2)
    polygon = np.concatenate([np.column_stack([center - width, ys]),
                              np.column_stack([center + width, ys])[::-1]]).astype(np.int32)
    cv2.fillPoly(image, [polygon], (54, 104, 110))
    cv2.polylines(image, [polygon], True, (92, 124, 113), 2)
    if scenario == "excavation" and frame:
        w, h = 45 + frame * 28, 50 + frame * 27
        cv2.rectangle(image, (64, 205), (64 + w, 205 + h), (161, 132, 91), -1)
        for inset in (8, 18, 30):
            cv2.rectangle(image, (64 + inset, 205 + inset),
                          (64 + w - inset, 205 + h - inset), (119, 99, 73), 3)
        cv2.line(image, (74, 205), (100, 80), (176, 154, 115), 6)
    image.setflags(write=False)
    return image


def fixture_manifest():
    return [{**f, "synthetic": True, "pixel_size_m": 2.0,
             "provenance": "Procedurally rendered illustration; assumed 2 m/pixel. Not satellite observations.",
             "frames": [{"index": i, "label": ["Baseline", "+6 hours", "+12 hours", "+18 hours"][i],
                         "date": f"2026-10-20T{str(i * 6).zfill(2)}:00:00Z",
                         "image_url": f"/api/v1/change/fixtures/{f['id']}/image?frame={i}"}
                        for i in range(4)]} for f in FIXTURES]


@lru_cache(maxsize=1)
def thermal_snapshot():
    """Read the existing committed snapshot without restoring a database."""
    directory = Path(__file__).resolve().parents[3] / "data" / "demo"
    classifications = {r["thermal_source_id"]: r for r in
                       (json.loads(line) for line in (directory / "classification.jsonl").read_text().splitlines())}
    features = []
    for line in (directory / "thermal_source.jsonl").read_text().splitlines():
        source = json.loads(line)
        classification = classifications.get(source["id"], {})
        properties = {key: source.get(key) for key in (
            "id", "first_seen", "last_seen", "span_days", "detection_count", "recurrence_days",
            "frp_mean", "bbox_area_km2", "bbox_growth_rate", "land_cover", "burn_scar", "dnbr")}
        properties.update({key: classification.get(key) for key in
                           ("predicted_class", "confidence", "is_unregistered", "rationale", "method")})
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates":
                         [source["centroid_lon"], source["centroid_lat"]]}, "properties": properties})
    return {"type": "FeatureCollection", "features": features,
            "provenance": "Historical thermal-source snapshot bundled with the prior project. Not live observations or newly validated classifications."}
