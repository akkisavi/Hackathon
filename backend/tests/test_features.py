"""Temporal feature derivation — pure, no DB."""
from __future__ import annotations

from datetime import datetime, timezone

from app.processing.features import temporal_features

_ROW = {
    "span_days": 120.0, "detection_count": 240, "recurrence_days": 90,
    "frp_mean": 8.0, "frp_std": 1.6, "frp_max": 40.0, "frp_trend": 0.02,
    "day_night_ratio": 0.5, "bbox_area_km2": 0.3, "bbox_growth_rate": 0.001,
    "first_seen": datetime(2025, 11, 3, tzinfo=timezone.utc),
}


def test_derived_fields():
    f = temporal_features(_ROW)
    assert f["frp_cv"] == 0.2                    # 1.6 / 8.0
    assert f["frp_spike_ratio"] == 5.0           # 40 / 8
    assert f["persistence"] == 0.75              # 90 distinct days / 120
    assert f["first_seen_month"] == 11
    assert f["detection_count"] == 240


def test_handles_zero_frp_mean():
    f = temporal_features({**_ROW, "frp_mean": 0.0, "frp_std": 0.0, "frp_max": 0.0})
    assert f["frp_cv"] == 0.0
    assert f["frp_spike_ratio"] == 0.0


def test_persistence_never_divides_by_zero():
    f = temporal_features({**_ROW, "span_days": 0.0, "recurrence_days": 1})
    assert f["persistence"] == 1.0
