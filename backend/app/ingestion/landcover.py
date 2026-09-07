"""ESA WorldCover 10 m land-cover sampling via Google Earth Engine.

`land_cover` at a thermal source's centroid is a cheap, strong prior:
cropland points that burn in Oct-Nov are almost certainly stubble;
built-up / bare points that burn persistently are almost certainly a
facility. The rule engine and LightGBM both consume it.

Auth: `earthengine authenticate` (user creds) + `GEE_PROJECT` in .env.
If either is missing this module is a graceful no-op — the rest of the
pipeline runs without land cover.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings

# ESA/WorldCover/v200 "Map" band codes
WORLDCOVER_CLASSES = {
    10: "tree_cover", 20: "shrubland", 30: "grassland", 40: "cropland",
    50: "built_up", 60: "bare", 70: "snow_ice", 80: "water",
    90: "wetland", 95: "mangroves", 100: "moss_lichen",
}
_CHUNK = 1000


@lru_cache(maxsize=1)
def _ee():
    """Import + initialise Earth Engine once, or return None if unavailable."""
    project = get_settings().gee_project
    if not project:
        return None
    try:
        import ee
        ee.Initialize(project=project)
        return ee
    except Exception as exc:  # not authed, no project access, offline
        print(f"land cover: Earth Engine unavailable ({str(exc)[:120]})")
        return None


def ee_available() -> bool:
    return _ee() is not None


def sample_land_cover(points: list[tuple[int, float, float]]) -> dict[int, str]:
    """points: [(source_id, lon, lat), ...] -> {source_id: land_cover_class}.
    Missing / offshore points are omitted. Returns {} if EE is unavailable."""
    ee = _ee()
    if ee is None or not points:
        return {}

    cover = ee.Image("ESA/WorldCover/v200/2021").select("Map")
    out: dict[int, str] = {}

    for i in range(0, len(points), _CHUNK):
        chunk = points[i:i + _CHUNK]
        fc = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([lon, lat]), {"sid": sid})
            for sid, lon, lat in chunk
        ])
        sampled = cover.reduceRegions(collection=fc, reducer=ee.Reducer.first(), scale=10)
        for feat in sampled.getInfo()["features"]:
            props = feat["properties"]
            code = props.get("first")
            if code is not None:
                out[int(props["sid"])] = WORLDCOVER_CLASSES.get(int(code), "unknown")

    return out
