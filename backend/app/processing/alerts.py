"""Alert list: unregistered / newly-appeared thermal sources.

Shared by the `/alerts` endpoint and the notification pipeline so both
agree on what counts as an alert.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.classification import Classification
from app.models.thermal_source import ThermalSource


def _alert_dict(s: ThermalSource, c: Classification | None) -> dict:
    return {
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
    }


def build_alerts(db: Session, new_within_days: int = 3) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=new_within_days)
    stmt = (
        select(ThermalSource, Classification)
        .join(Classification, Classification.thermal_source_id == ThermalSource.id, isouter=True)
        .where(or_(Classification.is_unregistered.is_(True), ThermalSource.first_seen >= cutoff))
        .order_by(Classification.is_unregistered.desc().nullslast(), ThermalSource.first_seen.desc())
    )
    return [_alert_dict(s, c) for s, c in db.execute(stmt).all()]


def get_alert(db: Session, source_id: int) -> dict | None:
    """One source as an alert dict, regardless of the new/unregistered
    window — used by the manual "send alert" button."""
    row = db.execute(
        select(ThermalSource, Classification)
        .join(Classification, Classification.thermal_source_id == ThermalSource.id, isouter=True)
        .where(ThermalSource.id == source_id)
    ).first()
    return _alert_dict(*row) if row else None
