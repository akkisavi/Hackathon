"""Clustered ThermalSource entities — the unit the system reasons about."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.report_generator import generate_narrative
from app.core.db import get_db
from app.core.geojson import feature_collection, point_feature
from app.models.classification import Classification
from app.models.thermal_source import ThermalSource
from app.models.user import User
from app.api.dependencies import get_current_user_or_api_key

router = APIRouter(prefix="/sources", tags=["sources"])

_LIFECYCLE_FIELDS = (
    "first_seen", "last_seen", "span_days", "detection_count", "recurrence_days",
    "frp_mean", "frp_std", "frp_max", "frp_trend",
    "day_count", "night_count", "day_night_ratio",
    "bbox_area_km2", "bbox_growth_rate", "land_cover", "dnbr", "burn_scar",
)


def _base_props(s: ThermalSource) -> dict:
    out = {"id": s.id}
    for f in _LIFECYCLE_FIELDS:
        v = getattr(s, f)
        out[f] = v.isoformat() if hasattr(v, "isoformat") else v
    return out


def _class_props(c: Classification | None) -> dict:
    if c is None:
        return {"predicted_class": None, "confidence": None, "is_unregistered": False}
    return {
        "predicted_class": c.predicted_class,
        "confidence": c.confidence,
        "is_unregistered": c.is_unregistered if c else None,
        "anomaly_score": c.anomaly_score,
        "estimated_bcm_per_year": c.estimated_bcm_per_year,
        "estimated_co2_tons_per_year": c.estimated_co2_tons_per_year,
        "estimated_value_inr": c.estimated_value_inr,
    }


@router.get("/")
def list_sources(
    min_detections: int = Query(1, ge=1),
    predicted_class: str | None = Query(None),
    unregistered_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key),
):
    stmt = (
        select(ThermalSource, Classification)
        .join(Classification, Classification.thermal_source_id == ThermalSource.id, isouter=True)
        .where(ThermalSource.detection_count >= min_detections)
        .order_by(ThermalSource.detection_count.desc())
    )
    if predicted_class:
        stmt = stmt.where(Classification.predicted_class == predicted_class)
    if unregistered_only:
        stmt = stmt.where(Classification.is_unregistered.is_(True))

    rows = db.execute(stmt).all()
    return feature_collection(
        point_feature(s.centroid_lon, s.centroid_lat, {
                      **_base_props(s), **_class_props(c)})
        for s, c in rows
    )


@router.get("/{source_id}")
def get_source(source_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_or_api_key)):
    s = db.get(ThermalSource, source_id)
    if s is None:
        raise HTTPException(status_code=404, detail="thermal source not found")

    c = db.execute(
        select(Classification).where(
            Classification.thermal_source_id == source_id)
    ).scalar_one_or_none()

    classification = None
    narrative = None
    if c is not None:
        classification = {
            **_class_props(c),
            "method": c.method,
            "rationale": c.rationale,
            "unregistered_reason": c.unregistered_reason,
            "scores": (c.features or {}).get("_scores"),
        }
        if c.narrative is None:
            c.narrative = generate_narrative(s, c, c.features or {})
            db.commit()
        narrative = c.narrative or None

    return {
        **point_feature(s.centroid_lon, s.centroid_lat, _base_props(s)),
        "classification": classification,
        "narrative": narrative,
    }
