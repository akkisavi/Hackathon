"""Load the EOG / VIIRS Nightfire global flare survey into `flare_ref`.

Reads every `eog_global_flare_survey_<year>_flare_list.csv` in a directory,
keeps points inside the India bounding box, and collapses the yearly rows
into one record per location with the span of years it was observed.

    python -m app.ingestion.flare_catalog ../data
"""
from __future__ import annotations

import glob
import os
import re
import sys

import pandas as pd
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.flare_ref import FlareRef

INDIA_BBOX = (68.0, 6.0, 98.0, 38.0)  # min_lon, min_lat, max_lon, max_lat
_YEAR_RE = re.compile(r"survey_(\d{4})_flare_list")


def _load_year(path: str) -> pd.DataFrame:
    year = int(_YEAR_RE.search(os.path.basename(path)).group(1))
    df = pd.read_csv(path, usecols=[
        "cntry_name", "latitude", "longitude", "flr_type", "flr_volume",
    ])
    lo_lon, lo_lat, hi_lon, hi_lat = INDIA_BBOX
    df = df[
        df.latitude.between(lo_lat, hi_lat) & df.longitude.between(lo_lon, hi_lon)
    ].copy()
    df["year"] = year
    return df


def load_flare_catalog(data_dir: str, db: Session) -> int:
    paths = sorted(glob.glob(os.path.join(data_dir, "eog_global_flare_survey_*_flare_list.csv")))
    if not paths:
        raise FileNotFoundError(f"no EOG flare survey CSVs in {data_dir}")

    allrows = pd.concat([_load_year(p) for p in paths], ignore_index=True)
    allrows["key"] = (
        allrows.latitude.round(3).astype(str) + "," + allrows.longitude.round(3).astype(str)
    )

    grouped = allrows.groupby("key").agg(
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
        flare_type=("flr_type", "first"),
        country=("cntry_name", "first"),
        first_year=("year", "min"),
        last_year=("year", "max"),
        years_seen=("year", "nunique"),
        flr_volume_bcm=("flr_volume", "mean"),
    ).reset_index(drop=True)

    db.query(FlareRef).delete()
    for r in grouped.itertuples(index=False):
        db.add(FlareRef(
            latitude=float(r.latitude), longitude=float(r.longitude),
            geom=f"SRID=4326;POINT({float(r.longitude)} {float(r.latitude)})",
            flare_type=(str(r.flare_type)[:32] if pd.notna(r.flare_type) else None),
            country=(str(r.country)[:64] if pd.notna(r.country) else None),
            first_year=int(r.first_year), last_year=int(r.last_year),
            years_seen=int(r.years_seen),
            flr_volume_bcm=(float(r.flr_volume_bcm) if pd.notna(r.flr_volume_bcm) else None),
        ))
    db.commit()
    return len(grouped)


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "../data"
    session = SessionLocal()
    try:
        n = load_flare_catalog(data_dir, session)
        print(f"Loaded {n} India flare locations into flare_ref")
    finally:
        session.close()
