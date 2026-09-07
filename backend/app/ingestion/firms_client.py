"""NASA FIRMS Area API client.

Phase 0 acceptance target: pull live FIRMS detections into a pandas
DataFrame. This hits the NRT (near-real-time) Area API, which is enough
to get data flowing on Day 1 while the full-year archive request (submit
separately, it's processed server-side and can take a while) is queued.

Register a free MAP_KEY at:
    https://firms.modaps.eosdis.nasa.gov/api/map_key/

Usage:
    python -m app.ingestion.firms_client
    # or
    from app.ingestion.firms_client import fetch_firms_detections
    df = fetch_firms_detections(days=3)
"""
from __future__ import annotations

from io import StringIO

import pandas as pd
import requests

from app.core.config import get_settings

# Canonical column set the rest of the backend (models, clustering) targets,
# regardless of which FIRMS product the CSV came from.
CANONICAL_COLUMNS = [
    "latitude", "longitude", "acquired_at", "daynight",
    "brightness", "frp", "confidence", "satellite", "instrument",
]

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Bounding box covering mainland India: min_lon,min_lat,max_lon,max_lat
INDIA_BBOX = "68,6,98,38"

# VIIRS_SNPP_NRT is the most reliable near-real-time source; MODIS_NRT is
# coarser resolution but a useful cross-check later.
DEFAULT_SOURCE = "VIIRS_SNPP_NRT"


def fetch_firms_detections(
    days: int = 3,
    bbox: str = INDIA_BBOX,
    source: str = DEFAULT_SOURCE,
    map_key: str | None = None,
) -> pd.DataFrame:
    """Fetch the last `days` of thermal-anomaly detections over `bbox`.

    Raises RuntimeError with FIRMS' own error text if the MAP_KEY is
    missing/invalid or the transaction limit is hit (FIRMS caps each key
    at 5000 transactions / 10 minutes).
    """
    settings = get_settings()
    key = map_key or settings.firms_map_key
    if not key:
        raise RuntimeError(
            "FIRMS_MAP_KEY is not set. Get a free key at "
            "https://firms.modaps.eosdis.nasa.gov/api/map_key/ and put it in .env"
        )

    url = f"{FIRMS_BASE_URL}/{key}/{source}/{bbox}/{days}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    # FIRMS returns HTTP 200 with a plain-text error body on bad key/limits,
    # not a non-2xx status — so check the payload shape.
    text = resp.text
    if not text.strip() or "Invalid" in text.splitlines()[0]:
        raise RuntimeError(f"FIRMS API error: {text[:200]}")

    df = pd.read_csv(StringIO(text))
    return df


def normalize_firms_df(df: pd.DataFrame) -> pd.DataFrame:
    """Map a raw FIRMS CSV frame onto `CANONICAL_COLUMNS`.

    Handles VIIRS (`bright_ti4`) and MODIS (`brightness`) column naming and
    parses `acq_date` + `acq_time` into a single UTC timestamp. Returns a
    new frame; drops rows with an unparseable timestamp or position.
    """
    if df.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    out = pd.DataFrame()
    out["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # acq_time is HHMM as an int/str ("44" -> 00:44, "1330" -> 13:30)
    hhmm = df["acq_time"].astype(str).str.zfill(4)
    out["acquired_at"] = pd.to_datetime(
        df["acq_date"].astype(str) + " " + hhmm,
        format="%Y-%m-%d %H%M", utc=True, errors="coerce",
    )

    out["daynight"] = df["daynight"].astype(str).str.upper().str[0]
    bright_col = "bright_ti4" if "bright_ti4" in df.columns else "brightness"
    out["brightness"] = pd.to_numeric(df[bright_col], errors="coerce")
    out["frp"] = pd.to_numeric(df["frp"], errors="coerce").fillna(0.0)
    out["confidence"] = df["confidence"].astype(str)
    out["satellite"] = df.get("satellite", "").astype(str)
    out["instrument"] = df.get("instrument", "").astype(str)

    out = out.dropna(subset=["latitude", "longitude", "acquired_at", "brightness"])
    return out[CANONICAL_COLUMNS].reset_index(drop=True)


if __name__ == "__main__":
    df = fetch_firms_detections(days=3)
    print(f"Fetched {len(df)} detections over India, last 3 days ({DEFAULT_SOURCE})")
    print(normalize_firms_df(df).head())
