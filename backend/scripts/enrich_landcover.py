"""Sample ESA WorldCover land cover for thermal sources and store it.

    python scripts/enrich_landcover.py           # all sources
    python scripts/enrich_landcover.py --missing  # only rows without land_cover

Needs `earthengine authenticate` + GEE_PROJECT in .env. Safe to re-run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal, engine
from app.ingestion.landcover import ee_available
from app.processing.pipeline import enrich_land_cover
from sqlalchemy import text


def _ensure_column() -> None:
    with engine.begin() as c:
        c.execute(text("ALTER TABLE thermal_source ADD COLUMN IF NOT EXISTS land_cover VARCHAR(16)"))


if __name__ == "__main__":
    if not ee_available():
        sys.exit("Earth Engine unavailable — run `earthengine authenticate` and set GEE_PROJECT.")
    _ensure_column()
    db = SessionLocal()
    try:
        n = enrich_land_cover(db, only_missing="--missing" in sys.argv)
        print(f"land cover written for {n} sources")
        for r in db.execute(text(
            "SELECT land_cover, count(*) FROM thermal_source GROUP BY 1 ORDER BY 2 DESC"
        )):
            print(f"  {r[0] or '(none)':16s} {r[1]}")
    finally:
        db.close()
