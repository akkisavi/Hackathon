"""Sentinel-2 burn-scar confirmation for wildfire candidates (Plan.md Stage 4).

    python scripts/confirm_wildfires.py

Needs `earthengine authenticate` + GEE_PROJECT in .env. Runs only on
sources predicted `wildfire` plus borderline candidates - a few dozen
GEE calls, not thousands. Safe to re-run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.core.db import SessionLocal, engine
from app.ingestion.landcover import ee_available
from app.processing.pipeline import confirm_wildfires


def _ensure_columns() -> None:
    with engine.begin() as c:
        c.execute(text("ALTER TABLE thermal_source ADD COLUMN IF NOT EXISTS dnbr DOUBLE PRECISION"))
        c.execute(text("ALTER TABLE thermal_source ADD COLUMN IF NOT EXISTS burn_scar VARCHAR(16)"))


if __name__ == "__main__":
    if not ee_available():
        sys.exit("Earth Engine unavailable - run `earthengine authenticate` and set GEE_PROJECT.")
    _ensure_columns()
    db = SessionLocal()
    try:
        print(confirm_wildfires(db))
        for r in db.execute(text(
            "SELECT burn_scar, count(*) FROM thermal_source WHERE dnbr IS NOT NULL GROUP BY 1"
        )):
            print(f"  {r[0]:10s} {r[1]}")
    finally:
        db.close()
