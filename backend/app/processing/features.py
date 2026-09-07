"""Per-source feature engineering for classification (Phase 2a).

Two halves:

* `temporal_features(row)` — pure, derived from the `thermal_source`
  lifecycle columns (day/night mix, persistence, FRP stability, footprint).
  These are the discriminators Plan.md leans on and they need no external
  data.
* `spatial_features(db)` — one set-based PostGIS pass that attaches the
  nearest-infrastructure and nearest-known-flare distances for every
  source. Degrades gracefully: if `osm_infra` / `flare_ref` are empty the
  distance columns come back `None` and `has_infra_context` is False, so
  the rule engine and the unregistered-source flag know the difference
  between "nothing nearby" and "we have no registry loaded".

`build_feature_frame(db)` merges both into one DataFrame keyed by
source id — the input to `app/processing/classify.py`.
"""
from __future__ import annotations

import math

import pandas as pd
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.osm_infra import OsmInfra
from app.models.thermal_source import ThermalSource

# infra kinds we compute a dedicated distance for (rest fold into "any")
_INFRA_KINDS = ("industrial", "power_plant", "quarry", "works")

# ordinal code for LightGBM (ESA WorldCover "Map" band values); -1 = unknown
_LAND_COVER_CODE = {
    "tree_cover": 10, "shrubland": 20, "grassland": 30, "cropland": 40,
    "built_up": 50, "bare": 60, "snow_ice": 70, "water": 80,
    "wetland": 90, "mangroves": 95, "moss_lichen": 100,
}


def _cv(mean: float, std: float) -> float:
    return float(std / mean) if mean else 0.0


def temporal_features(row: dict) -> dict:
    """Derived behavioural features from one `thermal_source` row dict."""
    span = float(row["span_days"])
    recurrence = int(row["recurrence_days"])
    frp_mean = float(row["frp_mean"])
    dnr = float(row["day_night_ratio"])
    span_ceil = max(math.ceil(span), 1)

    return {
        "span_days": round(span, 3),
        "detection_count": int(row["detection_count"]),
        "recurrence_days": recurrence,
        "frp_mean": round(frp_mean, 3),
        "frp_std": round(float(row["frp_std"]), 3),
        "frp_max": round(float(row["frp_max"]), 3),
        "frp_trend": round(float(row["frp_trend"]), 4),
        "frp_cv": round(_cv(frp_mean, float(row["frp_std"])), 4),
        "frp_spike_ratio": round(float(row["frp_max"]) / frp_mean, 3) if frp_mean else 0.0,
        "day_night_ratio": round(dnr, 4),
        # fraction of the days between first and last sighting it was actually seen
        "persistence": round(recurrence / span_ceil, 4),
        "bbox_area_km2": round(float(row["bbox_area_km2"]), 4),
        "bbox_growth_rate": round(float(row["bbox_growth_rate"]), 6),
        "first_seen_month": row["first_seen"].month,
        "land_cover": row.get("land_cover"),
        "land_cover_code": _LAND_COVER_CODE.get(row.get("land_cover"), -1),
    }


def spatial_features(db: Session) -> pd.DataFrame:
    """Nearest-infra / nearest-flare distances (metres) for every source,
    in a single round trip each. Columns are NULL when the reference table
    is empty."""
    has_infra = db.scalar(select(func.count()).select_from(OsmInfra)) > 0
    has_flare = db.scalar(
        text("SELECT count(*) FROM flare_ref")
    ) if _table_exists(db, "flare_ref") else 0

    ids = [r[0] for r in db.execute(select(ThermalSource.id)).all()]
    frame = pd.DataFrame({"id": ids}).set_index("id")
    frame["has_infra_context"] = bool(has_infra)

    if has_infra:
        nearest = db.execute(text("""
            SELECT ts.id,
                   n.kind AS nearest_infra_kind,
                   n.name AS nearest_infra_name,
                   n.d    AS dist_to_infra_m
            FROM thermal_source ts
            LEFT JOIN LATERAL (
                SELECT oi.kind, oi.name,
                       ST_Distance(oi.geom::geography, ts.geom::geography) AS d
                FROM osm_infra oi
                ORDER BY oi.geom <-> ts.geom
                LIMIT 1
            ) n ON true
        """)).all()
        frame = frame.join(pd.DataFrame(nearest, columns=[
            "id", "nearest_infra_kind", "nearest_infra_name", "dist_to_infra_m",
        ]).set_index("id"))

        for kind in _INFRA_KINDS:
            col = f"dist_to_{kind}_m"
            rows = db.execute(text(f"""
                SELECT ts.id, n.d FROM thermal_source ts
                LEFT JOIN LATERAL (
                    SELECT ST_Distance(oi.geom::geography, ts.geom::geography) AS d
                    FROM osm_infra oi WHERE oi.kind = :kind
                    ORDER BY oi.geom <-> ts.geom LIMIT 1
                ) n ON true
            """), {"kind": kind}).all()
            frame = frame.join(pd.DataFrame(rows, columns=["id", col]).set_index("id"))
    else:
        for col in ("nearest_infra_kind", "nearest_infra_name", "dist_to_infra_m",
                    *(f"dist_to_{k}_m" for k in _INFRA_KINDS)):
            frame[col] = None

    if has_flare:
        rows = db.execute(text("""
            SELECT ts.id, n.d FROM thermal_source ts
            LEFT JOIN LATERAL (
                SELECT ST_Distance(fr.geom::geography, ts.geom::geography) AS d
                FROM flare_ref fr ORDER BY fr.geom <-> ts.geom LIMIT 1
            ) n ON true
        """)).all()
        frame = frame.join(pd.DataFrame(rows, columns=["id", "dist_to_known_flare_m"]).set_index("id"))
    else:
        frame["dist_to_known_flare_m"] = None

    return frame


def _table_exists(db: Session, name: str) -> bool:
    return bool(db.scalar(text("SELECT to_regclass(:n)"), {"n": f"public.{name}"}))


def build_feature_frame(db: Session) -> pd.DataFrame:
    """One row per thermal source: temporal + spatial features, id-indexed."""
    sources = db.execute(select(ThermalSource)).scalars().all()
    if not sources:
        return pd.DataFrame()

    temporal = pd.DataFrame(
        {s.id: temporal_features(_row_dict(s)) for s in sources}
    ).T
    temporal.index.name = "id"

    spatial = spatial_features(db)
    return temporal.join(spatial)


def _row_dict(s: ThermalSource) -> dict:
    return {
        "span_days": s.span_days, "detection_count": s.detection_count,
        "recurrence_days": s.recurrence_days, "frp_mean": s.frp_mean,
        "frp_std": s.frp_std, "frp_max": s.frp_max, "frp_trend": s.frp_trend,
        "day_night_ratio": s.day_night_ratio, "bbox_area_km2": s.bbox_area_km2,
        "bbox_growth_rate": s.bbox_growth_rate, "first_seen": s.first_seen,
        "land_cover": s.land_cover,
    }
