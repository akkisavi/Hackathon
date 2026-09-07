"""Orchestration: FIRMS -> detections -> clustered sources -> classification.

`run_ingest_and_cluster` is the whole pipeline. It is called by the Celery
beat task (every 6 h) and by `POST /api/v1/ingest` for on-demand runs.
"""
from __future__ import annotations

import math
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.ingestion.firms_client import fetch_firms_detections, normalize_firms_df
from app.ingestion.landcover import sample_land_cover
from app.ingestion.persist import upsert_detections
from app.ingestion.sentinel import burn_scar_dnbr
from app.models.classification import Classification
from app.models.detection import Detection
from app.models.thermal_source import ThermalSource
from app.processing.classify import anomaly_scores, classify_one, is_unregistered
from app.processing.clustering import cluster_detections
from app.processing.features import build_feature_frame

# thermal_source is derived and rebuilt every run; the window must be wide
# enough to keep a persistent source's full history (that persistence is the
# whole classification signal) but not so wide it drowns in a year of
# transient crop-fire specks.
CLUSTER_WINDOW_DAYS = 400
_INSERT_CHUNK = 1000


def _significant(s) -> bool:
    """Keep persistent or intense sources; drop the long tail of 2-3 pixel
    one-offs that a full year of FIRMS produces."""
    return (
        s.recurrence_days >= 3 or s.span_days >= 7
        or s.frp_max >= 20.0 or s.detection_count >= 8
    )


def load_recent_detections(db: Session, days: int) -> pd.DataFrame:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(
        Detection.latitude, Detection.longitude, Detection.acquired_at,
        Detection.daynight, Detection.brightness, Detection.frp,
    ).where(Detection.acquired_at >= cutoff)
    rows = db.execute(stmt).all()
    return pd.DataFrame(rows, columns=[
        "latitude", "longitude", "acquired_at", "daynight", "brightness", "frp",
    ])


def rebuild_thermal_sources(
    db: Session, days: int = CLUSTER_WINDOW_DAYS, eps_km: float = 1.0, min_samples: int = 3
) -> int:
    """Re-cluster the recent detection window and replace `thermal_source`
    (classification rows cascade away with it)."""
    df = load_recent_detections(db, days)
    sources = [s for s in cluster_detections(df, eps_km=eps_km, min_samples=min_samples)
               if _significant(s)]

    db.query(ThermalSource).delete()
    rows = [
        {"geom": f"SRID=4326;POINT({s.centroid_lon} {s.centroid_lat})", **asdict(s)}
        for s in sources
    ]
    for i in range(0, len(rows), _INSERT_CHUNK):
        db.execute(insert(ThermalSource), rows[i:i + _INSERT_CHUNK])
    db.commit()
    return len(sources)


def enrich_land_cover(db: Session, only_missing: bool = False) -> int:
    """Sample ESA WorldCover at every source centroid and store it. No-op if
    Earth Engine isn't configured. Returns the number of rows updated."""
    q = select(ThermalSource.id, ThermalSource.centroid_lon, ThermalSource.centroid_lat)
    if only_missing:
        q = q.where(ThermalSource.land_cover.is_(None))
    points = [(r.id, float(r.centroid_lon), float(r.centroid_lat)) for r in db.execute(q).all()]
    covers = sample_land_cover(points)
    for sid, cls in covers.items():
        db.execute(
            ThermalSource.__table__.update()
            .where(ThermalSource.id == sid).values(land_cover=cls)
        )
    db.commit()
    return len(covers)


def _jsonsafe(v):
    if v is None:
        return None
    if hasattr(v, "item"):          # numpy scalar
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def classify_sources(db: Session) -> dict:
    """Stage-1 rule engine + Stage-3 anomaly flag for every thermal source."""
    frame = build_feature_frame(db)
    if frame.empty:
        return {"classified": 0, "unregistered": 0}

    scores = anomaly_scores(frame)
    cut = float(scores.quantile(0.85)) if (scores > 0).any() else float("inf")

    db.query(Classification).delete()
    n_unreg = 0
    batch = []
    for sid, row in frame.iterrows():
        f = {k: _jsonsafe(v) for k, v in row.to_dict().items()}
        pred = classify_one(f)
        a = float(scores.loc[sid])
        unreg, reason = is_unregistered(f, pred["predicted_class"], a, cut)
        n_unreg += int(unreg)
        batch.append({
            "thermal_source_id": int(sid),
            "predicted_class": pred["predicted_class"],
            "confidence": pred["confidence"],
            "method": pred["method"],
            "features": {**f, "_scores": pred["scores"]},
            "rationale": pred["rationale"],
            "anomaly_score": round(a, 4),
            "is_unregistered": unreg,
            "unregistered_reason": reason or None,
        })
    for i in range(0, len(batch), _INSERT_CHUNK):
        db.execute(insert(Classification), batch[i:i + _INSERT_CHUNK])
    db.commit()
    return {"classified": int(len(frame)), "unregistered": n_unreg}


def confirm_wildfires(db: Session, borderline_threshold: float = 0.6, max_borderline: int = 25) -> dict:
    """Stage 4: Sentinel-2 burn-scar check for every `wildfire` prediction
    plus the strongest borderline candidates (capped - each is a slow GEE
    call). Stores dNBR on `thermal_source` and folds the result into the
    classification rationale / confidence. No-op without EE."""
    from app.models.classification import Classification

    rows = db.execute(
        select(ThermalSource, Classification)
        .join(Classification, Classification.thermal_source_id == ThermalSource.id)
        .where(Classification.predicted_class == "wildfire")
    ).all()

    borderline = [
        (s, c, (c.features or {}).get("_scores", {}).get("wildfire", 0))
        for s, c in db.execute(
            select(ThermalSource, Classification)
            .join(Classification, Classification.thermal_source_id == ThermalSource.id)
            .where(Classification.predicted_class != "wildfire")
        ).all()
    ]
    borderline = [x for x in borderline if x[2] >= borderline_threshold]
    borderline.sort(key=lambda x: x[2], reverse=True)
    rows += [(s, c) for s, c, _ in borderline[:max_borderline]]

    checked = confirmed = denied = 0
    for s, c in rows:
        res = burn_scar_dnbr(s.centroid_lon, s.centroid_lat, s.first_seen, s.last_seen)
        if res is None:
            continue
        checked += 1
        s.dnbr, s.burn_scar = res["dnbr"], res["class"]
        if c.predicted_class == "wildfire":
            if res["class"] == "confirmed":
                confirmed += 1
                c.confidence = round(min(0.98, c.confidence + 0.1), 2)
                c.rationale += f"; Sentinel-2 burn scar confirmed (dNBR {res['dnbr']})"
            elif res["class"] == "none":
                denied += 1
                c.confidence = round(max(0.3, c.confidence - 0.2), 2)
                c.rationale += f"; no Sentinel-2 burn scar (dNBR {res['dnbr']}) - wildfire unconfirmed"
    db.commit()
    return {"burn_checked": checked, "burn_confirmed": confirmed, "burn_denied": denied}


def run_ingest_and_cluster(db: Session, days: int = 3) -> dict:
    raw = fetch_firms_detections(days=days)
    clean = normalize_firms_df(raw)
    added = upsert_detections(db, clean)
    source_count = rebuild_thermal_sources(db)
    covered = enrich_land_cover(db)
    cls = classify_sources(db)
    burn = confirm_wildfires(db)
    return {
        "fetched": len(raw), "new_detections": added,
        "thermal_sources": source_count, "land_cover_sampled": covered, **cls, **burn,
    }
