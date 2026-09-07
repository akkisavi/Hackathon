"""Clustering is the core of Phase 1 and needs no database — test it hard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from app.processing.clustering import cluster_detections


def _det(lat, lon, when, frp, daynight):
    return {
        "latitude": lat, "longitude": lon, "acquired_at": when,
        "frp": frp, "daynight": daynight,
    }


def _frame():
    t0 = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
    rows = []

    # Cluster A — Delhi, daytime only, FRP rising over 5 days -> positive trend
    for i in range(10):
        rows.append(_det(
            28.600 + (i % 3) * 0.001, 77.200 + (i % 2) * 0.001,
            t0 + timedelta(days=i * 0.5), 5.0 + i, "D",
        ))
    # Cluster B — Mumbai, even day/night split, flat FRP
    for i in range(6):
        rows.append(_det(
            19.000 + (i % 2) * 0.001, 72.800,
            t0 + timedelta(days=i * 0.5), 8.0, "D" if i % 2 == 0 else "N",
        ))
    # Noise — two lone pixels, far from everything and each other
    rows.append(_det(23.0, 80.0, t0, 4.0, "D"))
    rows.append(_det(15.0, 76.0, t0, 4.0, "N"))
    return pd.DataFrame(rows)


def test_recovers_two_clusters_and_drops_noise():
    sources = cluster_detections(_frame(), eps_km=1.0, min_samples=2)
    assert len(sources) == 2

    a, b = sources  # sorted by detection_count desc
    assert a.detection_count == 10
    assert b.detection_count == 6


def test_lifecycle_and_behaviour_features():
    a, b = cluster_detections(_frame(), eps_km=1.0, min_samples=2)

    # A: daytime-only, rising FRP
    assert a.day_night_ratio == 1.0
    assert a.night_count == 0
    assert a.frp_trend > 0
    assert a.recurrence_days == 5
    assert a.span_days > 4

    # B: balanced diurnal signature, flat FRP
    assert b.day_night_ratio == 0.5
    assert abs(b.frp_trend) < 1e-6
    assert b.frp_std == 0.0

    # both footprints are tiny (a fixed point source)
    assert a.bbox_area_km2 < 1.0
    assert b.bbox_area_km2 < 1.0


def test_empty_input():
    assert cluster_detections(pd.DataFrame(), eps_km=1.0) == []
