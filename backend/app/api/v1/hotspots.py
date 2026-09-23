"""Raw FIRMS detections as GeoJSON — the unclustered pixel layer."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.geojson import feature_collection, point_feature
from app.models.detection import Detection
from app.models.user import User
from app.api.dependencies import get_current_user_or_api_key

router = APIRouter(prefix="/hotspots", tags=["hotspots"])


@router.get("/")
def list_hotspots(
    days: int = Query(3, ge=1, le=60),
    limit: int = Query(5000, ge=1, le=20000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(Detection)
        .where(Detection.acquired_at >= cutoff)
        .order_by(Detection.acquired_at.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).scalars().all()
    return feature_collection(
        point_feature(d.longitude, d.latitude, {
            "acquired_at": d.acquired_at.isoformat(),
            "daynight": d.daynight,
            "brightness": d.brightness,
            "frp": d.frp,
            "confidence": d.confidence,
            "satellite": d.satellite,
        })
        for d in rows
    )
