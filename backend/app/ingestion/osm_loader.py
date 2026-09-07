"""Load OSM industrial / power / mining features into the `osm_infra` table.

Reads a Geofabrik `.osm.pbf` extract through GDAL's OSM driver (via
pyogrio). GDAL applies the attribute `where` filter *during* the read, so
this works directly on the full ~1.7 GB India extract without osmium
pre-filtering and without blowing up memory.

Kept tags (they drive the Phase 2 proximity features):

    landuse=industrial | quarry     power=plant     man_made=works

One representative point per feature is stored — enough for
nearest-distance features and sidesteps polygon/line inconsistency.

    python -m app.ingestion.osm_loader ../data/india-260906.osm.pbf
"""
from __future__ import annotations

import re
import sys

import geopandas as gpd
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.osm_infra import OsmInfra

_TAG_RE = re.compile(r'"([^"]+)"=>"([^"]*)"')
_TAG_KEYS = ("landuse", "power", "man_made")

# GDAL's default osmconf.ini promotes different tags per layer; `power` in
# particular is not a column on every layer. So each layer gets a primary
# WHERE (fast, precise) and a loose fallback that only touches `other_tags`
# (works everywhere; `classify()` filters precisely afterwards).
_LAYER_WHERE = {
    "multipolygons": [
        "landuse IN ('industrial','quarry') OR man_made = 'works' "
        "OR other_tags LIKE '%power%plant%'",
        "other_tags LIKE '%industrial%' OR other_tags LIKE '%quarry%' "
        "OR other_tags LIKE '%plant%' OR other_tags LIKE '%works%'",
    ],
    "points": [
        "other_tags LIKE '%power%plant%' OR other_tags LIKE '%man_made%works%' "
        "OR other_tags LIKE '%landuse%industrial%' OR other_tags LIKE '%landuse%quarry%'",
    ],
    "lines": [
        "man_made = 'works' OR other_tags LIKE '%works%' OR other_tags LIKE '%industrial%'",
        "other_tags LIKE '%works%' OR other_tags LIKE '%industrial%'",
    ],
}


def parse_other_tags(raw: str | None) -> dict[str, str]:
    return dict(_TAG_RE.findall(raw or ""))


def row_tags(row) -> dict[str, str]:
    tags = parse_other_tags(getattr(row, "other_tags", None))
    for key in _TAG_KEYS:
        val = getattr(row, key, None)
        if val:
            tags.setdefault(key, val)
    return tags


def classify(tags: dict[str, str]) -> str | None:
    if tags.get("landuse") == "industrial":
        return "industrial"
    if tags.get("landuse") == "quarry":
        return "quarry"
    if tags.get("power") == "plant":
        return "power_plant"
    if tags.get("man_made") == "works":
        return "works"
    return None


def load_osm_infra(pbf_path: str, db: Session) -> int:
    """Replace `osm_infra` with the matching features from `pbf_path`."""
    db.query(OsmInfra).delete()
    db.commit()
    written = 0

    for layer, where_options in _LAYER_WHERE.items():
        gdf = None
        for where in where_options:
            try:
                gdf = gpd.read_file(pbf_path, layer=layer, where=where, engine="pyogrio")
                break
            except Exception as e:  # WHERE rejected for this layer's columns
                print(f"  {layer}: WHERE rejected ({str(e)[:70]}), trying fallback")
        if gdf is None:
            print(f"  {layer}: skipped")
            continue
        if gdf.empty:
            print(f"  {layer}: 0 matches")
            continue

        batch = 0
        for row in gdf.itertuples(index=False):
            kind = classify(row_tags(row))
            geom = getattr(row, "geometry", None)
            if kind is None or geom is None or geom.is_empty:
                continue
            osm_id = getattr(row, "osm_id", None) or getattr(row, "osm_way_id", None)
            db.add(OsmInfra(
                osm_id=int(osm_id or 0), kind=kind,
                name=getattr(row, "name", None) or None,
                geom=f"SRID=4326;{geom.representative_point().wkt}",
            ))
            written += 1
            batch += 1
            if batch % 2000 == 0:
                db.commit()
        db.commit()
        print(f"  {layer}: +{batch} features")

    return written


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m app.ingestion.osm_loader <path-to.osm.pbf>")
    session = SessionLocal()
    try:
        n = load_osm_infra(sys.argv[1], session)
        print(f"Loaded {n} OSM infrastructure features into osm_infra")
    finally:
        session.close()
