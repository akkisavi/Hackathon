"""Spatio-temporal clustering of FIRMS detections into thermal sources.

FIRMS gives us thermal-anomaly *pixels*. The system reasons about
*sources* — a fixed location that keeps lighting up. We recover those with
DBSCAN on the detection positions (haversine metric, ~1 km neighbourhood),
then summarise each cluster's lifecycle and behaviour into the features
Plan.md identifies as the real discriminators (day/night mix, persistence,
FRP stability, footprint growth).

Pure functions, no DB — `app/processing/pipeline.py` does the I/O.

Deferred: splitting one location into separate episodes when it goes quiet
for weeks then reignites. The lifecycle features (span_days,
recurrence_days) already expose that, and archive data will make proper
episode segmentation worth doing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

EARTH_RADIUS_KM = 6371.0088
_KM_PER_DEG_LAT = 110.574
_KM_PER_DEG_LON_EQ = 111.320


@dataclass
class ClusteredSource:
    centroid_lat: float
    centroid_lon: float
    first_seen: datetime
    last_seen: datetime
    span_days: float
    detection_count: int
    recurrence_days: int
    frp_mean: float
    frp_std: float
    frp_max: float
    frp_trend: float
    day_count: int
    night_count: int
    day_night_ratio: float
    bbox_area_km2: float
    bbox_growth_rate: float


def _bbox_area_km2(lat: np.ndarray, lon: np.ndarray) -> float:
    if len(lat) < 2:
        return 0.0
    mean_lat_rad = np.radians(float(lat.mean()))
    h = (float(lat.max()) - float(lat.min())) * _KM_PER_DEG_LAT
    w = (float(lon.max()) - float(lon.min())) * _KM_PER_DEG_LON_EQ * np.cos(mean_lat_rad)
    return float(abs(h * w))


def _summarise(g: pd.DataFrame) -> ClusteredSource:
    g = g.sort_values("acquired_at")
    t = g["acquired_at"]
    first, last = t.iloc[0].to_pydatetime(), t.iloc[-1].to_pydatetime()
    span_days = (last - first).total_seconds() / 86400.0

    frp = g["frp"].to_numpy(dtype=float)
    day_offset = (t - t.iloc[0]).dt.total_seconds().to_numpy() / 86400.0
    if span_days > 0.01 and np.unique(day_offset).size >= 2:
        frp_trend = float(np.polyfit(day_offset, frp, 1)[0])
    else:
        frp_trend = 0.0

    lat = g["latitude"].to_numpy(dtype=float)
    lon = g["longitude"].to_numpy(dtype=float)
    total_area = _bbox_area_km2(lat, lon)
    if len(g) >= 4 and span_days >= 0.5:
        mid = t.iloc[0] + (t.iloc[-1] - t.iloc[0]) / 2
        early, late = g[t <= mid], g[t > mid]
        a_early = _bbox_area_km2(early["latitude"].to_numpy(float), early["longitude"].to_numpy(float))
        a_late = _bbox_area_km2(late["latitude"].to_numpy(float), late["longitude"].to_numpy(float))
        bbox_growth_rate = float((a_late - a_early) / span_days)
    else:
        bbox_growth_rate = 0.0

    day_count = int((g["daynight"] == "D").sum())
    night_count = int((g["daynight"] == "N").sum())
    lit = day_count + night_count

    return ClusteredSource(
        centroid_lat=float(lat.mean()),
        centroid_lon=float(lon.mean()),
        first_seen=first,
        last_seen=last,
        span_days=round(span_days, 4),
        detection_count=int(len(g)),
        recurrence_days=int(t.dt.date.nunique()),
        frp_mean=float(frp.mean()),
        frp_std=float(frp.std()),
        frp_max=float(frp.max()),
        frp_trend=round(frp_trend, 4),
        day_count=day_count,
        night_count=night_count,
        day_night_ratio=round(day_count / lit, 4) if lit else 0.0,
        bbox_area_km2=round(total_area, 4),
        bbox_growth_rate=round(bbox_growth_rate, 6),
    )


def cluster_detections(
    df: pd.DataFrame, eps_km: float = 1.0, min_samples: int = 2
) -> list[ClusteredSource]:
    """Cluster a normalized detection frame into `ClusteredSource` records.

    `df` needs columns: latitude, longitude, acquired_at (datetime),
    daynight ("D"/"N"), frp. DBSCAN noise points are dropped.
    """
    if df.empty:
        return []

    df = df.copy()
    df["acquired_at"] = pd.to_datetime(df["acquired_at"], utc=True)

    coords = np.radians(df[["latitude", "longitude"]].to_numpy(dtype=float))
    labels = DBSCAN(
        eps=eps_km / EARTH_RADIUS_KM,
        min_samples=min_samples,
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(coords)

    df["_cluster"] = labels
    sources = [
        _summarise(g) for label, g in df.groupby("_cluster") if label != -1
    ]
    sources.sort(key=lambda s: s.detection_count, reverse=True)
    return sources
