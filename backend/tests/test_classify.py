"""Rule-engine behaviour — pure, no DB."""
from __future__ import annotations

import pandas as pd

from app.processing.classify import anomaly_scores, is_unregistered, rule_classify

_BASE = {
    "span_days": 5.0, "detection_count": 10, "recurrence_days": 3,
    "frp_mean": 6.0, "frp_std": 3.0, "frp_max": 12.0, "frp_trend": 0.0,
    "frp_cv": 0.5, "frp_spike_ratio": 2.0, "day_night_ratio": 0.5,
    "persistence": 0.6, "bbox_area_km2": 0.5, "bbox_growth_rate": 0.0,
    "first_seen_month": 7, "has_infra_context": True,
    "dist_to_infra_m": 500.0, "dist_to_known_flare_m": 8000.0,
    "dist_to_power_plant_m": 500.0, "dist_to_industrial_m": 400.0,
    "dist_to_quarry_m": 9000.0, "dist_to_works_m": 600.0,
}


def feat(**over):
    return {**_BASE, **over}


def test_gas_flare_signature():
    f = feat(day_night_ratio=0.5, frp_cv=0.15, frp_std=0.9, span_days=120,
             recurrence_days=90, bbox_area_km2=0.2, dist_to_known_flare_m=200.0)
    out = rule_classify(f)
    assert out["predicted_class"] == "gas_flare"
    assert "flare" in out["rationale"]
    assert out["confidence"] >= 0.6


def test_agricultural_burning_signature():
    f = feat(day_night_ratio=0.95, frp_cv=0.9, frp_std=8.0, span_days=6,
             recurrence_days=4, bbox_area_km2=4.0, bbox_growth_rate=0.2,
             first_seen_month=11)
    assert rule_classify(f)["predicted_class"] == "agricultural_burning"


def test_wildfire_signature():
    f = feat(bbox_area_km2=25.0, bbox_growth_rate=1.2, span_days=9,
             day_night_ratio=0.8, frp_max=90.0, frp_trend=3.0)
    assert rule_classify(f)["predicted_class"] == "wildfire"


def test_mining_signature():
    f = feat(day_night_ratio=0.5, frp_cv=0.1, frp_std=0.5, span_days=200,
             recurrence_days=150, bbox_growth_rate=0.0, dist_to_quarry_m=300.0)
    assert rule_classify(f)["predicted_class"] == "mining"


def test_land_cover_pushes_cropland_toward_agriculture():
    base = feat(day_night_ratio=0.9, frp_cv=0.7, frp_std=6.0, span_days=8,
               recurrence_days=4, bbox_area_km2=1.8, first_seen_month=11)
    without = rule_classify({**base, "land_cover": None})
    withlc = rule_classify({**base, "land_cover": "cropland"})
    assert withlc["scores"]["agricultural_burning"] > without["scores"]["agricultural_burning"]
    assert withlc["predicted_class"] == "agricultural_burning"
    assert "cropland" in withlc["rationale"]


def test_land_cover_forest_pushes_toward_wildfire():
    f = feat(bbox_area_km2=12.0, bbox_growth_rate=0.4, span_days=10,
             day_night_ratio=0.75, frp_max=40.0, frp_trend=2.0, land_cover="tree_cover")
    out = rule_classify(f)
    assert out["predicted_class"] == "wildfire"
    assert "forest" in out["rationale"]


def test_no_infra_context_caps_confidence_and_notes_it():
    f = feat(has_infra_context=False, day_night_ratio=0.5, frp_cv=0.15,
             frp_std=0.9, span_days=120, recurrence_days=90, bbox_area_km2=0.2,
             dist_to_known_flare_m=200.0)
    out = rule_classify(f)
    assert out["confidence"] <= 0.70
    assert "no infrastructure registry" in out["rationale"]


def test_unknown_when_nothing_matches():
    f = feat(day_night_ratio=0.72, frp_cv=0.55, span_days=7, recurrence_days=2,
             bbox_area_km2=1.4, frp_spike_ratio=1.2, first_seen_month=7)
    # deliberately ambiguous — should not confidently pick a class
    out = rule_classify(f)
    assert out["predicted_class"] == "unknown" or out["confidence"] < 0.6


def test_is_unregistered_requires_infra_context():
    f = feat(has_infra_context=False)
    flag, reason = is_unregistered(f, "gas_flare", 0.9, 0.5)
    assert flag is False and "registry not loaded" in reason


def test_is_unregistered_fires_for_isolated_persistent_facility():
    f = feat(has_infra_context=True, span_days=120, recurrence_days=90,
             frp_cv=0.2, dist_to_infra_m=7000.0, dist_to_known_flare_m=9000.0)
    flag, reason = is_unregistered(f, "gas_flare", 0.9, 0.5)
    assert flag is True
    assert "nearest mapped facility" in reason


def test_anomaly_scores_zero_when_too_few_rows():
    frame = pd.DataFrame([_BASE] * 4)
    s = anomaly_scores(frame)
    assert (s == 0.0).all()
