"""Sentinel-2 burn-scar confirmation via Google Earth Engine (Plan.md Stage 4).

For a source the classifier calls a wildfire, a real vegetation fire leaves
a burn scar: NIR drops, SWIR rises. We compare a cloud-masked median
composite from *before* the fire window with one from *after* and read the
change in Normalized Burn Ratio:

    NBR   = (B8 - B12) / (B8 + B12)
    dNBR  = NBR_pre - NBR_post           (USGS: >0.10 low, >0.27 moderate, >0.44 high)

A clear positive dNBR confirms a burn; a flat dNBR next to a persistent
point source argues it is *not* a wildfire. Runs only on the handful of
wildfire candidates, not every source. No-op without `GEE_PROJECT`.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.ingestion.landcover import _ee  # shared ee.Initialize(project=...)

_PRE = (60, 5)    # composite window: 60d..5d before first_seen
_POST = (5, 60)   # 5d..60d after last_seen
_BUFFER_M = 200   # sample radius around the centroid
_MAX_CLOUD = 40

# dNBR interpretation (USGS burn-severity breaks)
LOW, MODERATE = 0.10, 0.27


def classify_dnbr(dnbr: float) -> str:
    """dNBR -> 'confirmed' (moderate+ burn) | 'low' | 'none'."""
    if dnbr >= MODERATE:
        return "confirmed"
    return "low" if dnbr >= LOW else "none"


def _nbr(ee, start: str, end: str, geom):
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geom)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", _MAX_CLOUD))
    )

    def mask(img):
        scl = img.select("SCL")
        clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))  # shadow/cloud/cirrus
        return img.updateMask(clear)

    masked = col.map(mask)
    count = masked.size()
    composite = masked.median()
    nbr = composite.normalizedDifference(["B8", "B12"]).rename("nbr")
    return nbr, count


def burn_scar_dnbr(lon: float, lat: float, first_seen: datetime, last_seen: datetime) -> dict | None:
    """Returns {"dnbr": float, "class": "confirmed"|"low"|"none", "scenes": [pre, post]}
    or None when Earth Engine is unavailable or there is not enough clear imagery."""
    ee = _ee()
    if ee is None:
        return None

    pt = ee.Geometry.Point([lon, lat])
    region = pt.buffer(_BUFFER_M)

    pre_s = (first_seen - timedelta(days=_PRE[0])).strftime("%Y-%m-%d")
    pre_e = (first_seen - timedelta(days=_PRE[1])).strftime("%Y-%m-%d")
    post_s = (last_seen + timedelta(days=_POST[0])).strftime("%Y-%m-%d")
    post_e = (last_seen + timedelta(days=_POST[1])).strftime("%Y-%m-%d")

    nbr_pre, n_pre = _nbr(ee, pre_s, pre_e, region)
    nbr_post, n_post = _nbr(ee, post_s, post_e, region)

    dnbr_img = nbr_pre.subtract(nbr_post).rename("dnbr")
    try:
        info = ee.Dictionary({
            "dnbr": dnbr_img.reduceRegion(ee.Reducer.mean(), region, 20).get("dnbr"),
            "n_pre": n_pre, "n_post": n_post,
        }).getInfo()
    except Exception:
        return None

    if info.get("dnbr") is None or not info["n_pre"] or not info["n_post"]:
        return None

    dnbr = round(float(info["dnbr"]), 4)
    return {"dnbr": dnbr, "class": classify_dnbr(dnbr),
            "scenes": [int(info["n_pre"]), int(info["n_post"])]}
