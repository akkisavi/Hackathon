"""Persist a normalized FIRMS frame into `detection` rows.

Uses INSERT ... ON CONFLICT DO NOTHING against the observation unique
constraint, so re-ingesting an overlapping time window is a cheap no-op.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.detection import Detection


def upsert_detections(db: Session, df: pd.DataFrame) -> int:
    """Insert new detections from a `normalize_firms_df` frame. Returns the
    number of rows actually added."""
    if df.empty:
        return 0

    rows = [
        {
            "latitude": float(r.latitude),
            "longitude": float(r.longitude),
            # EWKT string; GeoAlchemy2 wraps it in ST_GeomFromEWKT on insert
            "geom": f"SRID=4326;POINT({float(r.longitude)} {float(r.latitude)})",
            "acquired_at": r.acquired_at.to_pydatetime(),
            "daynight": (r.daynight or "D")[:1],
            "brightness": float(r.brightness),
            "frp": float(r.frp),
            "confidence": str(r.confidence)[:16],
            "satellite": str(r.satellite)[:16],
            "instrument": str(r.instrument)[:16],
        }
        for r in df.itertuples(index=False)
    ]

    # One multi-row INSERT per chunk (Core execution) so rowcount reports how
    # many actually landed after ON CONFLICT skips.
    added = 0
    for i in range(0, len(rows), 1000):
        chunk = rows[i:i + 1000]
        stmt = (
            insert(Detection)
            .values(chunk)
            .on_conflict_do_nothing(constraint="uq_detection_observation")
        )
        added += db.execute(stmt).rowcount or 0
    db.commit()
    return added
