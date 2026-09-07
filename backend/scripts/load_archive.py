"""One-off: bulk-load a FIRMS archive CSV into `detection`, then rebuild
and re-classify thermal sources over the full archive window.

    python scripts/load_archive.py ../data/fire_archive_SV-C2_800603.csv

The archive gives the months-of-history that the persistence / recurrence
features (and therefore the rule engine) actually need.
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal
from app.ingestion.firms_client import normalize_firms_df
from app.ingestion.persist import upsert_detections
from app.processing.pipeline import classify_sources, rebuild_thermal_sources

CHUNK = 50_000


def main(csv_path: str) -> None:
    db = SessionLocal()
    try:
        added = 0
        for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=CHUNK)):
            n = upsert_detections(db, normalize_firms_df(chunk))
            added += n
            print(f"  chunk {i}: +{n} detections (total {added})")

        t0 = time.time()
        n_src = rebuild_thermal_sources(db, days=400)
        print(f"clustered -> {n_src} thermal sources in {time.time() - t0:.0f}s")

        t0 = time.time()
        print("classify ->", classify_sources(db), f"in {time.time() - t0:.0f}s")
    finally:
        db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../data/fire_archive_SV-C2_800603.csv")
