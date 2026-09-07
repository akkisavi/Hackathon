"""Alert feed: unregistered / newly-appeared thermal sources (Phase 2b/3)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.classification import Classification
from app.models.thermal_source import ThermalSource

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
def list_alerts(new_within_days: int = Query(3, ge=1, le=30), db: Session = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=new_within_days)
    stmt = (
        select(ThermalSource, Classification)
        .join(Classification, Classification.thermal_source_id == ThermalSource.id, isouter=True)
        .where(or_(Classification.is_unregistered.is_(True), ThermalSource.first_seen >= cutoff))
        .order_by(Classification.is_unregistered.desc().nullslast(), ThermalSource.first_seen.desc())
    )
    alerts = []
    for s, c in db.execute(stmt).all():
        alerts.append({
            "source_id": s.id,
            "lat": s.centroid_lat, "lon": s.centroid_lon,
            "severity": "unregistered" if (c and c.is_unregistered) else "new",
            "predicted_class": c.predicted_class if c else None,
            "confidence": c.confidence if c else None,
            "reason": (c.unregistered_reason if (c and c.is_unregistered)
                       else f"first detected {s.first_seen.date()}"),
            "first_seen": s.first_seen.isoformat(),
            "last_seen": s.last_seen.isoformat(),
            "detection_count": s.detection_count,
        })
    return {"count": len(alerts), "alerts": alerts}
