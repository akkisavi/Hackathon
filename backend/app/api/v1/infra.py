"""OSM industrial / power / mining infrastructure as GeoJSON — the map
overlay the classifier's proximity features are computed against."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.geojson import feature_collection, point_feature
from app.models.osm_infra import OsmInfra

router = APIRouter(prefix="/infra", tags=["infra"])

_KINDS = ("industrial", "quarry", "power_plant", "works")


@router.get("/")
def list_infra(
    bbox: str | None = Query(None, description="minlon,minlat,maxlon,maxlat"),
    kind: str | None = Query(None, description="|".join(_KINDS)),
    limit: int = Query(4000, ge=1, le=20000),
    db: Session = Depends(get_db),
):
    stmt = select(
        OsmInfra.id, OsmInfra.kind, OsmInfra.name,
        func.ST_Y(OsmInfra.geom).label("lat"), func.ST_X(OsmInfra.geom).label("lon"),
    )
    if kind in _KINDS:
        stmt = stmt.where(OsmInfra.kind == kind)
    if bbox:
        lo_lon, lo_lat, hi_lon, hi_lat = (float(x) for x in bbox.split(","))
        stmt = stmt.where(
            func.ST_X(OsmInfra.geom).between(lo_lon, hi_lon),
            func.ST_Y(OsmInfra.geom).between(lo_lat, hi_lat),
        )
    rows = db.execute(stmt.limit(limit)).all()
    return feature_collection(
        point_feature(r.lon, r.lat, {"id": r.id, "kind": r.kind, "name": r.name})
        for r in rows
    )


@router.get("/counts")
def infra_counts(db: Session = Depends(get_db)):
    rows = db.execute(
        select(OsmInfra.kind, func.count()).group_by(OsmInfra.kind)
    ).all()
    return {"total": sum(n for _, n in rows), "by_kind": dict(rows)}
