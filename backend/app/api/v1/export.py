"""Export classified thermal sources for the evaluator's own GIS.

`?format=geojson` (default) or `?format=kml`. Same class / unregistered /
bbox filters as `/sources`. Returns a file download.
"""
from __future__ import annotations

import json
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.geojson import feature_collection, point_feature
from app.models.classification import Classification
from app.models.thermal_source import ThermalSource

router = APIRouter(prefix="/export", tags=["export"])

_PROPS = ("predicted_class", "confidence", "is_unregistered", "first_seen",
          "last_seen", "span_days", "recurrence_days", "detection_count",
          "frp_mean", "day_night_ratio")

_KML_COLOR = {  # aabbggrr
    "gas_flare": "ff0066ff", "mining": "ff00aaff", "steel_smelter": "ffff5555",
    "brick_kiln": "ff55aaff", "agricultural_burning": "ff33dd33",
    "wildfire": "ff0000cc", "industrial_fire": "ffff00ff", None: "ffcccccc",
}


def _rows(params: dict, db: Session):
    stmt = (
        select(ThermalSource, Classification)
        .join(Classification, Classification.thermal_source_id == ThermalSource.id, isouter=True)
        .order_by(ThermalSource.detection_count.desc())
    )
    if params.get("predicted_class"):
        stmt = stmt.where(Classification.predicted_class == params["predicted_class"])
    if params.get("unregistered_only"):
        stmt = stmt.where(Classification.is_unregistered.is_(True))
    if params.get("bbox"):
        lo_lon, lo_lat, hi_lon, hi_lat = (float(x) for x in params["bbox"].split(","))
        stmt = stmt.where(
            ThermalSource.centroid_lon.between(lo_lon, hi_lon),
            ThermalSource.centroid_lat.between(lo_lat, hi_lat),
        )
    return db.execute(stmt).all()


def _props(s: ThermalSource, c: Classification | None) -> dict:
    out = {"id": s.id}
    for k in _PROPS:
        v = getattr(c, k, None) if k in ("predicted_class", "confidence", "is_unregistered") \
            else getattr(s, k, None)
        out[k] = v.isoformat() if hasattr(v, "isoformat") else v
    return out


def _kml(rows) -> str:
    marks = []
    for s, c in rows:
        cls = c.predicted_class if c else None
        name = f"#{s.id} {cls or 'unclassified'}"
        desc = "; ".join(f"{k}={v}" for k, v in _props(s, c).items())
        marks.append(
            f'<Placemark><name>{escape(name)}</name>'
            f'<description>{escape(desc)}</description>'
            f'<Style><IconStyle><color>{_KML_COLOR.get(cls, _KML_COLOR[None])}</color></IconStyle></Style>'
            f'<Point><coordinates>{s.centroid_lon},{s.centroid_lat},0</coordinates></Point></Placemark>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        '<name>SIH26162 thermal sources</name>' + "".join(marks) +
        '</Document></kml>'
    )


@router.get("/")
def export(
    format: str = Query("geojson", pattern="^(geojson|kml)$"),
    predicted_class: str | None = None,
    unregistered_only: bool = False,
    bbox: str | None = None,
    db: Session = Depends(get_db),
):
    rows = _rows(
        {"predicted_class": predicted_class, "unregistered_only": unregistered_only, "bbox": bbox},
        db,
    )
    if format == "kml":
        return Response(
            _kml(rows), media_type="application/vnd.google-earth.kml+xml",
            headers={"Content-Disposition": 'attachment; filename="thermal_sources.kml"'},
        )
    fc = feature_collection(
        point_feature(s.centroid_lon, s.centroid_lat, _props(s, c)) for s, c in rows
    )
    return Response(
        json.dumps(fc), media_type="application/geo+json",
        headers={"Content-Disposition": 'attachment; filename="thermal_sources.geojson"'},
    )
